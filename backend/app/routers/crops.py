from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_role
from app.database import get_db
from app.models import CropListing, User, UserRole
from app.schemas import CropListingCreate, CropListingOut, CropListingBulkSync
from datetime import datetime, timezone

router = APIRouter(prefix="/crop-listings", tags=["crop-listings"])


@router.post("", response_model=CropListingOut, status_code=201)
def create_listing(
    payload: CropListingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.FARMER, UserRole.STUDENT_AGENT)),
):
    listing = CropListing(farmer_id=user.id, synced_at=datetime.now(timezone.utc), **payload.model_dump())
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


@router.post("/sync", response_model=List[CropListingOut])
def bulk_sync(
    payload: CropListingBulkSync,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.FARMER, UserRole.STUDENT_AGENT)),
):
    """The mobile app calls this once when connectivity returns, flushing
    every offline scan queued in local SQLite/Hive. Dedupes on
    offline_scan_uuid so a retried sync never double-creates listings."""
    created = []
    for item in payload.listings:
        if item.offline_scan_uuid:
            existing = (
                db.query(CropListing)
                .filter(CropListing.offline_scan_uuid == item.offline_scan_uuid)
                .first()
            )
            if existing:
                created.append(existing)
                continue
        listing = CropListing(farmer_id=user.id, synced_at=datetime.now(timezone.utc), **item.model_dump())
        db.add(listing)
        db.flush()
        created.append(listing)
    db.commit()
    for listing in created:
        db.refresh(listing)
    return created


@router.get("", response_model=List[CropListingOut])
def list_listings(
    crop_type: str = None,
    status: str = "available",
    db: Session = Depends(get_db),
):
    query = db.query(CropListing).filter(CropListing.status == status)
    if crop_type:
        query = query.filter(CropListing.crop_type == crop_type)
    return query.order_by(CropListing.created_at.desc()).limit(200).all()


@router.get("/mine", response_model=List[CropListingOut])
def my_listings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(CropListing).filter(CropListing.farmer_id == user.id).all()
