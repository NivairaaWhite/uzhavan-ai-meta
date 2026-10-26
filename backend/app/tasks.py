"""
Background jobs: price scraping, fair-price recomputation, logistics
pooling, notifications, and server-side Meta AI crop grade audits.
"""
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
from bs4 import BeautifulSoup

from app.celery_app import celery_app
from app.config import get_settings
from app.database import SessionLocal
from app.models import (
    MarketPrice, CropListing, LogisticsPool, LogisticsPoolMember, ProcessingUnit,
)
from app.services.pricing import compute_fair_price
from app.services.matching import cluster_listings, PoolCandidate
from app.services.meta_ai import MetaAIUnavailable
from app.services.grade_audit import audit_grade

logger = logging.getLogger(__name__)
settings = get_settings()

TRACKED_CROPS = ["tomato", "onion", "paddy", "brinjal", "banana", "chilli"]
TN_DISTRICTS = ["Coimbatore", "Madurai", "Salem", "Erode", "Tiruchirappalli"]


@celery_app.task(name="app.tasks.scrape_agmarknet_prices")
def scrape_agmarknet_prices():
    inserted = 0
    with SessionLocal() as db:
        for crop in TRACKED_CROPS:
            try:
                rows = _fetch_agmarknet_for_crop(crop)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Agmarknet scrape failed for %s: %s", crop, exc)
                continue
            for row in rows:
                db.add(MarketPrice(
                    crop_type=crop,
                    market_name=row["market_name"],
                    district=row["district"],
                    wholesale_price_per_kg=row["price_per_kg"],
                    source="agmarknet",
                    recorded_date=row.get("date", datetime.now(timezone.utc)),
                ))
                inserted += 1
        db.commit()
    logger.info("scrape_agmarknet_prices inserted %d rows", inserted)
    return inserted


def _fetch_agmarknet_for_crop(crop: str) -> list[dict]:
    if settings.OGD_INDIA_API_KEY:
        url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
        params = {
            "api-key": settings.OGD_INDIA_API_KEY,
            "format": "json",
            "filters[commodity]": crop,
            "filters[state]": "Tamil Nadu",
            "limit": 50,
        }
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            records = resp.json().get("records", [])
        return [
            {
                "market_name": r.get("market", "Unknown"),
                "district": r.get("district", "Unknown"),
                "price_per_kg": float(r.get("modal_price", 0)) / 100,
                "date": datetime.strptime(r["arrival_date"], "%d/%m/%Y") if r.get("arrival_date") else datetime.now(timezone.utc),
            }
            for r in records if r.get("modal_price")
        ]

    url = f"{settings.AGMARKNET_BASE_URL}/PriceAndArrivalReports/PriceAndArrivalReport.aspx"
    with httpx.Client(timeout=15) as client:
        resp = client.get(url, params={"commodity": crop, "state": "TN"})
        resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    rows = []
    for tr in soup.select("table#ctl00_cphBody_gridRecords tr")[1:]:
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) >= 5:
            rows.append({
                "market_name": cells[1],
                "district": cells[0],
                "price_per_kg": float(cells[4].replace(",", "")) / 100,
            })
    return rows


@celery_app.task(name="app.tasks.scrape_retail_prices")
def scrape_retail_prices():
    logger.info("scrape_retail_prices: no compliant public retail price feed configured")
    return 0


@celery_app.task(name="app.tasks.recompute_fair_prices")
def recompute_fair_prices():
    """Recomputes fair_price_per_kg for every open crop_listing using the
    latest MarketPrice row for its (crop_type, district)."""
    updated = 0
    with SessionLocal() as db:
        listings = db.query(CropListing).filter(CropListing.status == "available").all()
        for listing in listings:
            q = db.query(MarketPrice).filter(MarketPrice.crop_type == listing.crop_type)
            if listing.district:
                q = q.filter(MarketPrice.district == listing.district)
            latest = q.order_by(MarketPrice.recorded_date.desc()).first()

            if not latest:
                # Fallback without district
                latest = (
                    db.query(MarketPrice)
                    .filter(MarketPrice.crop_type == listing.crop_type)
                    .order_by(MarketPrice.recorded_date.desc())
                    .first()
                )
            if not latest:
                continue

            result = compute_fair_price(
                wholesale_price_per_kg=latest.wholesale_price_per_kg,
                retail_price_per_kg=latest.retail_price_per_kg,
            )
            listing.fair_price_per_kg = result.fair_price_per_kg
            updated += 1
        db.commit()
    logger.info("recompute_fair_prices updated %d listings", updated)
    return updated


@celery_app.task(name="app.tasks.run_logistics_pooling")
def run_logistics_pooling():
    """Groups available same-crop listings per district into logistics
    pools once enough nearby farmers have unsold stock."""
    created = 0
    with SessionLocal() as db:
        crop_types = [r[0] for r in db.query(CropListing.crop_type).distinct()]
        for crop in crop_types:
            listings = (
                db.query(CropListing)
                .filter(CropListing.crop_type == crop, CropListing.status == "available")
                .all()
            )
            if not listings:
                continue
            candidates = [
                PoolCandidate(l.id, l.latitude, l.longitude, l.quantity_kg) for l in listings
            ]
            pools = cluster_listings(candidates)
            for pool in pools:
                district = listings[0].district or (listings[0].farmer.district if listings[0].farmer else "Unknown")
                lp = LogisticsPool(
                    district=district,
                    crop_type=crop,
                    centroid_lat=pool.centroid_lat,
                    centroid_lng=pool.centroid_lng,
                    total_quantity_kg=pool.total_quantity_kg,
                    status="ready",
                )
                db.add(lp)
                db.flush()
                for listing_id in pool.member_listing_ids:
                    db.add(LogisticsPoolMember(pool_id=lp.id, listing_id=listing_id))
                    db.query(CropListing).filter(CropListing.id == listing_id).update({"status": "pooled"})
                created += 1
        db.commit()
    logger.info("run_logistics_pooling created %d pools", created)
    return created


@celery_app.task(name="app.tasks.reset_daily_processing_intake")
def reset_daily_processing_intake():
    with SessionLocal() as db:
        updated = db.query(ProcessingUnit).filter(ProcessingUnit.is_active.is_(True)).update(
            {ProcessingUnit.remaining_intake_today_kg: ProcessingUnit.daily_intake_capacity_kg}
        )
        db.commit()
    logger.info("reset_daily_processing_intake reset %d units", updated)
    return updated


@celery_app.task(name="app.tasks.audit_listing_grade")
def audit_listing_grade(listing_id: str):
    """Server-side AI audit of a synced scan photo.
    Evaluates with Spark 1.3 vision; escalates to Wonder 1.0 on disagreement.
    The on-device grade stays the farmer's record; audit provides buyer verification."""
    with SessionLocal() as db:
        listing = db.get(CropListing, listing_id)
        if not listing or not listing.image_path:
            return "no image"

        try:
            with open(listing.image_path, "rb") as f:
                jpeg = f.read()
            v = audit_grade(jpeg, listing.crop_type)
            model_used = settings.META_MODEL_FAST

            if v.grade != listing.grade.value:
                # Disagreement escalation to Muse Wonder
                logger.info("Audit disagreement for listing %s (%s vs %s): escalating to %s",
                            listing_id, listing.grade.value, v.grade, settings.META_MODEL_DEEP)
                try:
                    v = audit_grade(jpeg, listing.crop_type, model=settings.META_MODEL_DEEP)
                    model_used = settings.META_MODEL_DEEP
                except Exception as esc_err:
                    logger.warning("Wonder escalation failed, retaining Spark verdict: %s", esc_err)

        except (MetaAIUnavailable, FileNotFoundError) as exc:
            listing.audit_status = "skipped"
            db.commit()
            logger.warning("audit skipped for %s: %s", listing_id, exc)
            return "skipped"
        except Exception as exc:
            listing.audit_status = "skipped"
            db.commit()
            logger.error("audit error for %s: %s", listing_id, exc)
            return "skipped"

        listing.audit_grade = v.grade
        listing.audit_confidence = v.confidence
        listing.audit_defects = json.dumps(v.defects)
        listing.audit_model = model_used
        listing.audit_status = "agree" if v.grade == listing.grade.value else "disagree"
        db.commit()
        return listing.audit_status
