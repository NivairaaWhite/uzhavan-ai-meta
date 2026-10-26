import json
from dataclasses import asdict
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_role
from app.database import get_db
from app.models import (
    CropSpoilageProfile,
    PostHarvestRecommendation,
    ProcessingUnit,
    StorageFacility,
    User,
    UserRole,
)
from app.schemas import (
    CropSpoilageProfileOut,
    CropSpoilageProfileUpsert,
    PostHarvestRecommendationHistoryOut,
    PostHarvestRecommendationOut,
    PostHarvestRecommendationRequest,
    ProcessingUnitCreate,
    ProcessingUnitOut,
    StorageFacilityCreate,
    StorageFacilityOut,
)
from app.services.post_harvest_advisor import recommend_allocation
from app.services.advisor_explainer import explain

router = APIRouter(prefix="/post-harvest", tags=["post-harvest"])


@router.post("/recommend", response_model=PostHarvestRecommendationOut)
def recommend(
    payload: PostHarvestRecommendationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.FARMER, UserRole.STUDENT_AGENT)),
):
    """Deterministic 'what should I do with this crop today?' endpoint.
    Logged to post_harvest_recommendations."""
    try:
        result = recommend_allocation(
            db,
            crop_type=payload.crop_type,
            quantity_kg=payload.quantity_kg,
            district=payload.district,
            latitude=payload.latitude,
            longitude=payload.longitude,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    def _kg(channel: str) -> float:
        return sum(a.quantity_kg for a in result.allocations if a.channel == channel)

    record = PostHarvestRecommendation(
        farmer_id=user.id,
        listing_id=payload.listing_id,
        crop_type=result.crop_type,
        quantity_kg=result.quantity_kg,
        district=payload.district,
        latitude=payload.latitude,
        longitude=payload.longitude,
        perishability_tier=result.perishability_tier,
        sell_now_kg=_kg("sell_now"),
        store_kg=_kg("store"),
        process_kg=_kg("process"),
        at_risk_kg=_kg("at_risk"),
        wholesale_price_per_kg=result.wholesale_price_per_kg,
        expected_net_value=result.expected_net_value,
        baseline_sell_all_today_value=result.baseline_sell_all_today_value,
        projected_savings=result.projected_savings,
        reasoning="\n".join(result.reasoning),
        allocation_detail_json=json.dumps([asdict(a) for a in result.allocations]),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return PostHarvestRecommendationOut(
        id=record.id,
        crop_type=result.crop_type,
        quantity_kg=result.quantity_kg,
        perishability_tier=result.perishability_tier,
        allocations=result.allocations,
        wholesale_price_per_kg=result.wholesale_price_per_kg,
        expected_net_value=result.expected_net_value,
        baseline_sell_all_today_value=result.baseline_sell_all_today_value,
        projected_savings=result.projected_savings,
        reasoning=result.reasoning,
        created_at=record.created_at,
    )


@router.get("/{rec_id}/explanation")
def get_explanation(
    rec_id: str,
    lang: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Fetches or generates a natural Tamil/English explanation via Muse Spark."""
    rec = (
        db.query(PostHarvestRecommendation)
        .filter(
            PostHarvestRecommendation.id == rec_id,
            PostHarvestRecommendation.farmer_id == user.id,
        )
        .first()
    )
    if not rec:
        raise HTTPException(404, "Recommendation not found")

    target_lang = lang or user.preferred_language or "ta"

    if rec.explanation and rec.explanation_lang == target_lang:
        return {"explanation": rec.explanation, "lang": target_lang}

    facts = {
        "crop": rec.crop_type,
        "quantity_kg": rec.quantity_kg,
        "district": rec.district,
        "sell_now_kg": rec.sell_now_kg,
        "store_kg": rec.store_kg,
        "process_kg": rec.process_kg,
        "at_risk_kg": rec.at_risk_kg,
        "expected_net_value_rupees": rec.expected_net_value,
        "sell_everything_today_rupees": rec.baseline_sell_all_today_value,
        "extra_rupees_earned": rec.projected_savings,
        "channels": json.loads(rec.allocation_detail_json or "[]"),
    }

    text = explain(facts, target_lang)
    if text is None:
        return {"explanation": None, "lang": target_lang}

    rec.explanation = text
    rec.explanation_lang = target_lang
    db.commit()
    return {"explanation": text, "lang": target_lang}


@router.get("/history", response_model=List[PostHarvestRecommendationHistoryOut])
def history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(PostHarvestRecommendation)
        .filter(PostHarvestRecommendation.farmer_id == user.id)
        .order_by(PostHarvestRecommendation.created_at.desc())
        .limit(50)
        .all()
    )


@router.get("/storage-facilities", response_model=List[StorageFacilityOut])
def list_storage_facilities(
    district: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(StorageFacility).filter(StorageFacility.is_active.is_(True))
    if district:
        query = query.filter(StorageFacility.district == district)
    return query.all()


@router.post("/storage-facilities", response_model=StorageFacilityOut, status_code=201)
def create_storage_facility(
    payload: StorageFacilityCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    facility = StorageFacility(**payload.model_dump())
    db.add(facility)
    db.commit()
    db.refresh(facility)
    return facility


@router.get("/processing-units", response_model=List[ProcessingUnitOut])
def list_processing_units(
    district: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(ProcessingUnit).filter(ProcessingUnit.is_active.is_(True))
    if district:
        query = query.filter(ProcessingUnit.district == district)
    return query.all()


@router.post("/processing-units", response_model=ProcessingUnitOut, status_code=201)
def create_processing_unit(
    payload: ProcessingUnitCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    unit = ProcessingUnit(**payload.model_dump())
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


@router.get("/spoilage-profiles", response_model=List[CropSpoilageProfileOut])
def list_spoilage_profiles(db: Session = Depends(get_db)):
    return db.query(CropSpoilageProfile).all()


@router.put("/spoilage-profiles", response_model=CropSpoilageProfileOut)
def upsert_spoilage_profile(
    payload: CropSpoilageProfileUpsert,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    crop_type = payload.crop_type.strip().lower()
    row = db.query(CropSpoilageProfile).filter(CropSpoilageProfile.crop_type == crop_type).first()
    fields = payload.model_dump(exclude={"crop_type"})
    if row:
        for key, value in fields.items():
            setattr(row, key, value)
    else:
        row = CropSpoilageProfile(crop_type=crop_type, **fields)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row
