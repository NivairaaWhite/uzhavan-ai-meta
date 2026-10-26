from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MarketPrice
from app.schemas import MarketPriceOut, FairPriceResponse
from app.services.pricing import compute_fair_price

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/prices", response_model=List[MarketPriceOut])
def get_prices(
    crop_type: str = Query(...),
    district: Optional[str] = None,
    days: int = 7,
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    query = db.query(MarketPrice).filter(
        MarketPrice.crop_type == crop_type, MarketPrice.recorded_date >= since
    )
    if district:
        query = query.filter(MarketPrice.district == district)
    return query.order_by(MarketPrice.recorded_date.desc()).limit(100).all()


@router.get("/fair-price", response_model=FairPriceResponse)
def get_fair_price(
    crop_type: str = Query(...),
    district: str = Query(...),
    db: Session = Depends(get_db),
):
    latest = (
        db.query(MarketPrice)
        .filter(MarketPrice.crop_type == crop_type, MarketPrice.district == district)
        .order_by(MarketPrice.recorded_date.desc())
        .first()
    )
    if not latest:
        raise HTTPException(status_code=404, detail="No price data yet for this crop/district")
    result = compute_fair_price(
        wholesale_price_per_kg=latest.wholesale_price_per_kg,
        retail_price_per_kg=latest.retail_price_per_kg,
    )
    return FairPriceResponse(
        crop_type=crop_type,
        district=district,
        wholesale_price_per_kg=result.wholesale_price_per_kg,
        retail_price_per_kg=result.retail_price_per_kg,
        fair_price_per_kg=result.fair_price_per_kg,
        farmer_share_pct=result.farmer_share_pct,
    )
