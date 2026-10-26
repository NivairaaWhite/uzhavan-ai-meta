"""
Core schema. Five domain tables as specified (users, crop_listings,
market_prices, orders, logistics_pools) plus a pool-membership join table
and a price-quality-audit table needed to make grading trustworthy.
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_id() -> str:
    return uuid.uuid4().hex


class UserRole(str, enum.Enum):
    FARMER = "farmer"
    STUDENT_AGENT = "student_agent"
    BUYER = "buyer"
    ADMIN = "admin"


class CropGrade(str, enum.Enum):
    GRADE_A = "grade_a"
    GRADE_B = "grade_b"
    GRADE_C = "grade_c"
    REJECTED = "rejected"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    ESCROW_HELD = "escrow_held"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    RELEASED = "released"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class KycStatus(str, enum.Enum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class PerishabilityTier(str, enum.Enum):
    HIGHLY_PERISHABLE = "highly_perishable"   # tomato, brinjal, banana, leafy greens
    SEMI_PERISHABLE = "semi_perishable"       # onion, chilli
    DURABLE = "durable"                       # paddy, other grains/pulses


class User(Base):
    __tablename__ = "users"

    id = Column(String(32), primary_key=True, default=gen_id)
    full_name = Column(String(120), nullable=False)
    phone_number = Column(String(15), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.FARMER)
    preferred_language = Column(String(8), default="ta")  # ISO code, e.g. ta, hi, en
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    village = Column(String(120), nullable=True)
    district = Column(String(120), nullable=True)
    state = Column(String(120), default="Tamil Nadu")
    bank_account_masked = Column(String(20), nullable=True)   # last 4 digits only, ever
    bank_ifsc = Column(String(11), nullable=True)
    kyc_status = Column(Enum(KycStatus), default=KycStatus.UNVERIFIED)
    kyc_reference_id = Column(String(64), nullable=True)      # DigiLocker txn ref, not raw docs
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    crop_listings = relationship("CropListing", back_populates="farmer")
    orders_as_buyer = relationship("Order", back_populates="buyer")


class CropListing(Base):
    __tablename__ = "crop_listings"

    id = Column(String(32), primary_key=True, default=gen_id)
    farmer_id = Column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    crop_type = Column(String(80), nullable=False, index=True)   # e.g. tomato, paddy, brinjal
    grade = Column(Enum(CropGrade), nullable=False)
    grade_confidence = Column(Float, nullable=True)   # edge-model softmax confidence, 0-1
    quantity_kg = Column(Float, nullable=False)
    target_price_per_kg = Column(Float, nullable=True)   # farmer's ask, optional
    fair_price_per_kg = Column(Float, nullable=True)     # last computed platform fair price
    district = Column(String(120), nullable=True, index=True) # Explicit district for pooling & prices
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    scan_image_ref = Column(String(255), nullable=True)  # local or object storage key
    offline_scan_uuid = Column(String(64), nullable=True, index=True)  # dedupe key from device
    status = Column(String(20), default="available")  # available, pooled, sold, expired
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    synced_at = Column(DateTime, nullable=True)  # null until the offline scan reaches the server

    # --- Meta AI audit (Phase 3) ---
    image_path = Column(String(255), nullable=True)
    audit_status = Column(String(16), default="none")   # none, pending, agree, disagree, skipped
    audit_grade = Column(String(16), nullable=True)
    audit_confidence = Column(Float, nullable=True)
    audit_defects = Column(Text, nullable=True)         # JSON list
    audit_model = Column(String(40), nullable=True)

    farmer = relationship("User", back_populates="crop_listings")
    pool_memberships = relationship("LogisticsPoolMember", back_populates="listing")


class MarketPrice(Base):
    __tablename__ = "market_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    crop_type = Column(String(80), nullable=False, index=True)
    market_name = Column(String(120), nullable=False)   # e.g. Koyambedu mandi
    district = Column(String(120), nullable=False, index=True)
    state = Column(String(120), default="Tamil Nadu")
    wholesale_price_per_kg = Column(Float, nullable=False)
    retail_price_per_kg = Column(Float, nullable=True)
    source = Column(String(40), nullable=False)  # agmarknet, bigbasket, zepto, blinkit, manual
    recorded_date = Column(DateTime, nullable=False, index=True)
    fetched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Order(Base):
    __tablename__ = "orders"

    id = Column(String(32), primary_key=True, default=gen_id)
    listing_id = Column(String(32), ForeignKey("crop_listings.id"), nullable=False)
    buyer_id = Column(String(32), ForeignKey("users.id"), nullable=False)
    quantity_kg = Column(Float, nullable=False)
    agreed_price_per_kg = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    razorpay_order_id = Column(String(64), nullable=True)
    razorpay_payment_id = Column(String(64), nullable=True)
    escrow_release_ref = Column(String(64), nullable=True)
    delivery_deadline = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    buyer = relationship("User", back_populates="orders_as_buyer")
    listing = relationship("CropListing")


class LogisticsPool(Base):
    __tablename__ = "logistics_pools"

    id = Column(String(32), primary_key=True, default=gen_id)
    district = Column(String(120), nullable=False)
    crop_type = Column(String(80), nullable=False)
    centroid_lat = Column(Float, nullable=False)
    centroid_lng = Column(Float, nullable=False)
    total_quantity_kg = Column(Float, default=0.0)
    status = Column(String(20), default="forming")  # forming, ready, dispatched, completed
    route_polyline = Column(Text, nullable=True)     # encoded OSRM/Google route
    estimated_distance_km = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    dispatched_at = Column(DateTime, nullable=True)

    members = relationship("LogisticsPoolMember", back_populates="pool")


class LogisticsPoolMember(Base):
    __tablename__ = "logistics_pool_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pool_id = Column(String(32), ForeignKey("logistics_pools.id"), nullable=False)
    listing_id = Column(String(32), ForeignKey("crop_listings.id"), nullable=False)

    pool = relationship("LogisticsPool", back_populates="members")
    listing = relationship("CropListing", back_populates="pool_memberships")


class CropSpoilageProfile(Base):
    __tablename__ = "crop_spoilage_profiles"

    crop_type = Column(String(80), primary_key=True)
    tier = Column(Enum(PerishabilityTier), nullable=False)
    shelf_life_ambient_days = Column(Float, nullable=False)
    shelf_life_cold_storage_days = Column(Float, nullable=False)
    daily_value_decay_pct = Column(Float, nullable=False)  # fraction of value lost per day at ambient temp
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class StorageFacility(Base):
    __tablename__ = "storage_facilities"

    id = Column(String(32), primary_key=True, default=gen_id)
    name = Column(String(160), nullable=False)
    district = Column(String(120), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    capacity_kg = Column(Float, nullable=False)
    available_capacity_kg = Column(Float, nullable=False)
    cost_per_kg_per_day = Column(Float, nullable=False)
    supported_crop_types = Column(Text, nullable=True)  # comma-separated, "*" = all
    contact_phone = Column(String(15), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ProcessingUnit(Base):
    __tablename__ = "processing_units"

    id = Column(String(32), primary_key=True, default=gen_id)
    name = Column(String(160), nullable=False)
    district = Column(String(120), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    output_product = Column(String(120), nullable=True)  # e.g. "tomato puree"
    daily_intake_capacity_kg = Column(Float, nullable=False)
    remaining_intake_today_kg = Column(Float, nullable=False)
    price_per_kg = Column(Float, nullable=False)  # what the unit pays per kg of raw crop
    accepted_crop_types = Column(Text, nullable=True)  # comma-separated, "*" = all
    contact_phone = Column(String(15), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PostHarvestRecommendation(Base):
    __tablename__ = "post_harvest_recommendations"

    id = Column(String(32), primary_key=True, default=gen_id)
    farmer_id = Column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    listing_id = Column(String(32), ForeignKey("crop_listings.id"), nullable=True)
    crop_type = Column(String(80), nullable=False, index=True)
    quantity_kg = Column(Float, nullable=False)
    district = Column(String(120), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    perishability_tier = Column(Enum(PerishabilityTier), nullable=False)
    sell_now_kg = Column(Float, default=0.0)
    store_kg = Column(Float, default=0.0)
    process_kg = Column(Float, default=0.0)
    at_risk_kg = Column(Float, default=0.0)
    wholesale_price_per_kg = Column(Float, nullable=True)
    expected_net_value = Column(Float, nullable=True)
    baseline_sell_all_today_value = Column(Float, nullable=True)
    projected_savings = Column(Float, nullable=True)
    reasoning = Column(Text, nullable=True)              # newline-joined human-readable bullets
    allocation_detail_json = Column(Text, nullable=True)  # full per-channel/facility breakdown
    explanation = Column(Text, nullable=True)            # Meta AI generated Tamil explanation
    explanation_lang = Column(String(8), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    farmer = relationship("User")
    listing = relationship("CropListing")
