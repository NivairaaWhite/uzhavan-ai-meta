import os
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_role
from app.config import get_settings
from app.database import get_db
from app.models import CropListing, User, UserRole
from app.schemas import CropListingCreate, CropListingOut, CropListingBulkSync

settings = get_settings()
router = APIRouter(prefix="/crop-listings", tags=["crop-listings"])


@router.post("", response_model=CropListingOut, status_code=201)
def create_listing(
    payload: CropListingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.FARMER, UserRole.STUDENT_AGENT)),
):
    district = payload.district or user.district
    listing = CropListing(
        farmer_id=user.id,
        district=district,
        synced_at=datetime.now(timezone.utc),
        **payload.model_dump(exclude={"district"}),
    )
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
        district = item.district or user.district
        listing = CropListing(
            farmer_id=user.id,
            district=district,
            synced_at=datetime.now(timezone.utc),
            **item.model_dump(exclude={"district"}),
        )
        db.add(listing)
        db.flush()
        created.append(listing)
    db.commit()
    for listing in created:
        db.refresh(listing)
    return created


@router.get("", response_model=List[CropListingOut])
def list_listings(
    crop_type: Optional[str] = None,
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


@router.post("/{listing_id}/image")
def upload_image(
    listing_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.FARMER, UserRole.STUDENT_AGENT)),
):
    """Uploads scan photo, scrubs EXIF/GPS metadata, resizes for efficiency,
    and queues background server-side AI audit."""
    listing = (
        db.query(CropListing)
        .filter(CropListing.id == listing_id, CropListing.farmer_id == user.id)
        .first()
    )
    if not listing:
        raise HTTPException(404, "Listing not found")

    try:
        from PIL import Image, ImageOps
    except ImportError:
        raise HTTPException(500, "Pillow library is required for image processing")

    try:
        img = ImageOps.exif_transpose(Image.open(file.file)).convert("RGB")
        img.thumbnail((1024, 1024))
        clean = Image.new("RGB", img.size)
        clean.paste(img)  # Strip all EXIF metadata

        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        path = os.path.join(settings.UPLOAD_DIR, f"{listing.id}.jpg")
        clean.save(path, "JPEG", quality=80)

        listing.image_path = path
        listing.audit_status = "pending"
        db.commit()

        # Enqueue background Celery audit
        from app.tasks import audit_listing_grade
        audit_listing_grade.delay(listing.id)
        return {"status": "queued", "image_path": path}
    except Exception as exc:
        raise HTTPException(400, f"Failed to process image: {exc}")


@router.get("/{listing_id}/outline")
def get_outline(
    listing_id: str,
    concept: str = "tomato",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """SAM 3.1 segmentation outline extraction for produce photo."""
    listing = db.query(CropListing).filter(CropListing.id == listing_id).first()
    if not listing or not listing.image_path:
        raise HTTPException(404, "Listing or image not found")

    try:
        from app.services.meta_ai import segment
        with open(listing.image_path, "rb") as f:
            raw_bytes = f.read()
        res = segment(raw_bytes, concept)
        return {"listing_id": listing_id, "concept": concept, "outline": res}
    except Exception as exc:
        raise HTTPException(503, f"SAM segmentation unavailable: {exc}")
