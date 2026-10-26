"""Pydantic request/response schemas — kept separate from ORM models so the
API contract can evolve independently of the DB schema."""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict

from app.models import UserRole, CropGrade, OrderStatus, KycStatus, PerishabilityTier


# ---------- Users / Auth ----------

class UserCreate(BaseModel):
    full_name: str
    phone_number: str = Field(pattern=r"^\+?[0-9]{10,13}$")
    password: str = Field(min_length=6)
    role: UserRole = UserRole.FARMER
    preferred_language: str = "ta"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    village: Optional[str] = None
    district: Optional[str] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    full_name: str
    phone_number: str
    role: UserRole
    preferred_language: str
    district: Optional[str] = None
    kyc_status: KycStatus
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Crop Listings ----------

class CropListingCreate(BaseModel):
    crop_type: str
    grade: CropGrade
    grade_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    quantity_kg: float = Field(gt=0)
    target_price_per_kg: Optional[float] = Field(default=None, ge=0)
    latitude: float
    longitude: float
    scan_image_ref: Optional[str] = None
    offline_scan_uuid: Optional[str] = None   # lets the phone dedupe on re-sync


class CropListingBulkSync(BaseModel):
    """Body for POST /crop-listings/sync — the phone flushes its offline
    SQLite/Hive queue here once it regains connectivity."""
    listings: List[CropListingCreate]


class CropListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    farmer_id: str
    crop_type: str
    grade: CropGrade
    grade_confidence: Optional[float]
    quantity_kg: float
    target_price_per_kg: Optional[float]
    fair_price_per_kg: Optional[float]
    latitude: float
    longitude: float
    status: str
    created_at: datetime
    synced_at: Optional[datetime]


# ---------- Market Prices ----------

class MarketPriceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    crop_type: str
    market_name: str
    district: str
    wholesale_price_per_kg: float
    retail_price_per_kg: Optional[float]
    source: str
    recorded_date: datetime


class FairPriceResponse(BaseModel):
    crop_type: str
    district: str
    wholesale_price_per_kg: float
    retail_price_per_kg: Optional[float]
    fair_price_per_kg: float
    farmer_share_pct: float


# ---------- Orders ----------

class OrderCreate(BaseModel):
    listing_id: str
    quantity_kg: float = Field(gt=0)
    delivery_deadline: Optional[datetime] = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    listing_id: str
    buyer_id: str
    quantity_kg: float
    agreed_price_per_kg: float
    total_amount: float
    status: OrderStatus
    razorpay_order_id: Optional[str]
    created_at: datetime


# ---------- Logistics ----------

class LogisticsPoolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    district: str
    crop_type: str
    centroid_lat: float
    centroid_lng: float
    total_quantity_kg: float
    status: str
    estimated_distance_km: Optional[float]
    created_at: datetime


# ---------- Post-harvest advisor ----------

class StorageFacilityCreate(BaseModel):
    name: str
    district: str
    latitude: float
    longitude: float
    capacity_kg: float = Field(gt=0)
    available_capacity_kg: float = Field(ge=0)
    cost_per_kg_per_day: float = Field(ge=0)
    supported_crop_types: Optional[str] = None  # comma-separated, "*" = all
    contact_phone: Optional[str] = None


class StorageFacilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    district: str
    latitude: float
    longitude: float
    capacity_kg: float
    available_capacity_kg: float
    cost_per_kg_per_day: float
    supported_crop_types: Optional[str]
    is_active: bool


class ProcessingUnitCreate(BaseModel):
    name: str
    district: str
    latitude: float
    longitude: float
    output_product: Optional[str] = None
    daily_intake_capacity_kg: float = Field(gt=0)
    remaining_intake_today_kg: float = Field(ge=0)
    price_per_kg: float = Field(gt=0)
    accepted_crop_types: Optional[str] = None  # comma-separated, "*" = all
    contact_phone: Optional[str] = None


class ProcessingUnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    district: str
    latitude: float
    longitude: float
    output_product: Optional[str]
    daily_intake_capacity_kg: float
    remaining_intake_today_kg: float
    price_per_kg: float
    accepted_crop_types: Optional[str]
    is_active: bool


class CropSpoilageProfileUpsert(BaseModel):
    crop_type: str
    tier: PerishabilityTier
    shelf_life_ambient_days: float = Field(gt=0)
    shelf_life_cold_storage_days: float = Field(gt=0)
    daily_value_decay_pct: float = Field(ge=0, le=1)


class CropSpoilageProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    crop_type: str
    tier: PerishabilityTier
    shelf_life_ambient_days: float
    shelf_life_cold_storage_days: float
    daily_value_decay_pct: float


class PostHarvestRecommendationRequest(BaseModel):
    crop_type: str
    quantity_kg: float = Field(gt=0)
    district: str
    latitude: float
    longitude: float
    listing_id: Optional[str] = None  # link to an existing crop_listings row, if any


class AllocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    channel: str  # sell_now | store | process | at_risk
    quantity_kg: float
    unit_price_per_kg: Optional[float] = None
    estimated_value: Optional[float] = None
    facility_name: Optional[str] = None
    facility_id: Optional[str] = None
    distance_km: Optional[float] = None
    note: str = ""


class PostHarvestRecommendationOut(BaseModel):
    id: Optional[str] = None
    crop_type: str
    quantity_kg: float
    perishability_tier: PerishabilityTier
    allocations: List[AllocationOut]
    wholesale_price_per_kg: Optional[float]
    expected_net_value: Optional[float]
    baseline_sell_all_today_value: Optional[float]
    projected_savings: Optional[float]
    reasoning: List[str]
    created_at: Optional[datetime] = None


class PostHarvestRecommendationHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    crop_type: str
    quantity_kg: float
    perishability_tier: PerishabilityTier
    sell_now_kg: float
    store_kg: float
    process_kg: float
    at_risk_kg: float
    expected_net_value: Optional[float]
    projected_savings: Optional[float]
    created_at: datetime
