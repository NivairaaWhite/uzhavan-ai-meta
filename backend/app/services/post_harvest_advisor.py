"""
Post-Harvest Decision Advisor.

Answers "what should I do with this crop today?" by allocating a farmer's
freshly-harvested quantity across four channels — sell now, cold-store,
send to processing, or (when nothing nearby can absorb it in time) flag as
at-risk — using whatever real capacity and price data the platform has for
that crop/location today.

This is deliberately a transparent, tunable heuristic, not a black-box
model: every threshold is a Settings field (see config.py,
POST_HARVEST_*), and every recommendation returns the `reasoning` that
produced it, because a farmer acting on this needs to be able to sanity
check it, not just trust it. Swap the allocation loop below for a proper
constrained optimizer (e.g. PuLP/OR-Tools maximizing net value subject to
capacity constraints) once there's enough real facility/order data for
that to outperform this greedy pass — the `recommend_allocation()`
contract doesn't need to change. See docs/ARCHITECTURE.md.

Honesty notes on data:
- Local buyer demand isn't directly observable (no point-of-sale feed
  into this platform), so `_estimate_daily_demand_kg` proxies it from the
  platform's own recent Order volume for the crop. That only sees
  platform-mediated sales, not a farmer's other outlets (local mandi,
  door-to-door) — treat "sell now" as a floor, not a ceiling, until
  enough order history accumulates.
- Storage/processing capacity numbers come from whatever a facility (or
  an admin on its behalf) last reported via the onboarding endpoints in
  routers/post_harvest.py — there is no public real-time feed for this.
- The "distress sale" baseline below is an explicit, documented
  assumption for comparison purposes only (see Settings) — it is never
  used to tell a farmer what they will actually be paid.
"""
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    CropListing,
    CropSpoilageProfile,
    MarketPrice,
    Order,
    PerishabilityTier,
    ProcessingUnit,
    StorageFacility,
)
from app.services.pricing import compute_fair_price

settings = get_settings()

EARTH_RADIUS_KM = 6371.0088

# Fallback profiles for crops with no admin-tuned CropSpoilageProfile row
# yet (see models.CropSpoilageProfile). Tiers/day-counts are directional —
# grounded in general post-harvest handling guidance for these crops, not
# lab data — and meant to be corrected per-crop via the admin endpoint
# once real spoilage outcomes are observed.
DEFAULT_SPOILAGE_PROFILES = {
    "tomato":  dict(tier=PerishabilityTier.HIGHLY_PERISHABLE, shelf_life_ambient_days=3,   shelf_life_cold_storage_days=14,  daily_value_decay_pct=0.12),
    "brinjal": dict(tier=PerishabilityTier.HIGHLY_PERISHABLE, shelf_life_ambient_days=4,   shelf_life_cold_storage_days=12,  daily_value_decay_pct=0.10),
    "banana":  dict(tier=PerishabilityTier.HIGHLY_PERISHABLE, shelf_life_ambient_days=5,   shelf_life_cold_storage_days=21,  daily_value_decay_pct=0.09),
    "chilli":  dict(tier=PerishabilityTier.SEMI_PERISHABLE,   shelf_life_ambient_days=7,   shelf_life_cold_storage_days=30,  daily_value_decay_pct=0.05),
    "onion":   dict(tier=PerishabilityTier.SEMI_PERISHABLE,   shelf_life_ambient_days=45,  shelf_life_cold_storage_days=150, daily_value_decay_pct=0.01),
    "paddy":   dict(tier=PerishabilityTier.DURABLE,           shelf_life_ambient_days=270, shelf_life_cold_storage_days=365, daily_value_decay_pct=0.002),
}
GENERIC_FALLBACK_PROFILE = dict(
    tier=PerishabilityTier.SEMI_PERISHABLE, shelf_life_ambient_days=10,
    shelf_life_cold_storage_days=45, daily_value_decay_pct=0.04,
)


@dataclass
class SpoilageProfile:
    crop_type: str
    tier: PerishabilityTier
    shelf_life_ambient_days: float
    shelf_life_cold_storage_days: float
    daily_value_decay_pct: float


@dataclass
class ChannelAllocation:
    channel: str  # "sell_now" | "store" | "process" | "at_risk"
    quantity_kg: float
    unit_price_per_kg: Optional[float] = None
    estimated_value: Optional[float] = None
    facility_name: Optional[str] = None
    facility_id: Optional[str] = None
    distance_km: Optional[float] = None
    note: str = ""


@dataclass
class RecommendationResult:
    crop_type: str
    quantity_kg: float
    perishability_tier: PerishabilityTier
    allocations: List[ChannelAllocation]
    wholesale_price_per_kg: Optional[float]
    expected_net_value: Optional[float]
    baseline_sell_all_today_value: Optional[float]
    projected_savings: Optional[float]
    reasoning: List[str] = field(default_factory=list)


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _matches_crop(csv_field: Optional[str], crop_type: str) -> bool:
    """Empty/None field = no restriction recorded, treated as accepting
    anything (matches how onboarding forms are expected to be filled in:
    leave blank rather than list every crop)."""
    if not csv_field:
        return True
    allowed = [c.strip().lower() for c in csv_field.split(",") if c.strip()]
    return "*" in allowed or crop_type.lower() in allowed


def get_spoilage_profile(db: Session, crop_type: str) -> SpoilageProfile:
    row = db.query(CropSpoilageProfile).filter(CropSpoilageProfile.crop_type == crop_type).first()
    if row:
        return SpoilageProfile(
            crop_type=crop_type,
            tier=row.tier,
            shelf_life_ambient_days=row.shelf_life_ambient_days,
            shelf_life_cold_storage_days=row.shelf_life_cold_storage_days,
            daily_value_decay_pct=row.daily_value_decay_pct,
        )
    defaults = DEFAULT_SPOILAGE_PROFILES.get(crop_type, GENERIC_FALLBACK_PROFILE)
    return SpoilageProfile(crop_type=crop_type, **defaults)


def _latest_market_price(db: Session, crop_type: str, district: str) -> Optional[MarketPrice]:
    return (
        db.query(MarketPrice)
        .filter(MarketPrice.crop_type == crop_type, MarketPrice.district == district)
        .order_by(MarketPrice.recorded_date.desc())
        .first()
    )


def _estimate_daily_demand_kg(db: Session, crop_type: str) -> float:
    """Proxy for 'how much of this crop the local market absorbs per day' —
    see module honesty note above."""
    since = datetime.now(timezone.utc) - timedelta(days=settings.POST_HARVEST_DEMAND_LOOKBACK_DAYS)
    rows = (
        db.query(Order.quantity_kg)
        .join(CropListing, Order.listing_id == CropListing.id)
        .filter(CropListing.crop_type == crop_type, Order.created_at >= since)
        .all()
    )
    total_kg = sum(r[0] for r in rows)
    return total_kg / settings.POST_HARVEST_DEMAND_LOOKBACK_DAYS if total_kg > 0 else 0.0


def _nearby_storage(
    db: Session, crop_type: str, lat: float, lng: float, radius_km: float
) -> List[Tuple[float, StorageFacility]]:
    facilities = (
        db.query(StorageFacility)
        .filter(StorageFacility.is_active.is_(True), StorageFacility.available_capacity_kg > 0)
        .all()
    )
    matches = [
        (_haversine_km(lat, lng, f.latitude, f.longitude), f)
        for f in facilities
        if _matches_crop(f.supported_crop_types, crop_type)
    ]
    matches = [m for m in matches if m[0] <= radius_km]
    matches.sort(key=lambda m: (m[0], m[1].cost_per_kg_per_day))  # nearest, then cheapest
    return matches


def _nearby_processing(
    db: Session, crop_type: str, lat: float, lng: float, radius_km: float
) -> List[Tuple[float, ProcessingUnit]]:
    units = (
        db.query(ProcessingUnit)
        .filter(ProcessingUnit.is_active.is_(True), ProcessingUnit.remaining_intake_today_kg > 0)
        .all()
    )
    matches = [
        (_haversine_km(lat, lng, u.latitude, u.longitude), u)
        for u in units
        if _matches_crop(u.accepted_crop_types, crop_type)
    ]
    matches = [m for m in matches if m[0] <= radius_km]
    matches.sort(key=lambda m: (-m[1].price_per_kg, m[0]))  # best price, then nearest
    return matches


def recommend_allocation(
    db: Session,
    crop_type: str,
    quantity_kg: float,
    district: str,
    latitude: float,
    longitude: float,
    radius_km: Optional[float] = None,
) -> RecommendationResult:
    if quantity_kg <= 0:
        raise ValueError("quantity_kg must be positive")

    crop_type = crop_type.strip().lower()
    radius_km = settings.POST_HARVEST_MAX_FACILITY_RADIUS_KM if radius_km is None else radius_km
    profile = get_spoilage_profile(db, crop_type)
    reasoning: List[str] = []

    price_row = _latest_market_price(db, crop_type, district)
    sell_price: Optional[float] = None
    if price_row:
        fair = compute_fair_price(price_row.wholesale_price_per_kg, price_row.retail_price_per_kg)
        sell_price = fair.fair_price_per_kg
        reasoning.append(
            f"Using latest {district} wholesale price \u20b9{price_row.wholesale_price_per_kg:.2f}/kg "
            f"\u2192 fair price \u20b9{sell_price:.2f}/kg after the platform's farmer-share split."
        )
    else:
        reasoning.append(
            f"No recent market price on file for {crop_type} in {district} — the quantity "
            "split below is still valid, but rupee value estimates are not shown."
        )

    daily_demand = _estimate_daily_demand_kg(db, crop_type)
    if daily_demand <= 0:
        daily_demand = quantity_kg * settings.POST_HARVEST_NO_HISTORY_SELL_FRACTION
        reasoning.append(
            f"No recent platform order history for {crop_type} yet — the sell-now estimate "
            f"uses a conservative default ({settings.POST_HARVEST_NO_HISTORY_SELL_FRACTION:.0%} "
            "of the lot) instead of live demand; this improves automatically as orders accumulate."
        )
    else:
        reasoning.append(
            f"Recent platform demand for {crop_type} has averaged {daily_demand:.0f} kg/day "
            f"over the last {settings.POST_HARVEST_DEMAND_LOOKBACK_DAYS} days."
        )

    remaining = quantity_kg
    allocations: List[ChannelAllocation] = []
    gross_value = 0.0
    total_cost = 0.0
    any_value_computed = False

    # 1. Sell now — capped at what the local market has actually been
    # absorbing, so this never recommends dumping the whole lot into a
    # market that can't clear it and would just crash the farmer's price.
    sell_now = min(remaining, daily_demand)
    if sell_now > 0:
        value = sell_now * sell_price if sell_price else None
        if value is not None:
            gross_value += value
            any_value_computed = True
        allocations.append(ChannelAllocation(
            channel="sell_now", quantity_kg=round(sell_now, 1),
            unit_price_per_kg=sell_price,
            estimated_value=round(value, 2) if value is not None else None,
            note="Sell today at the current fair price — this is what the local market can absorb.",
        ))
        remaining -= sell_now

    # 2. Store — only worth considering if cold storage meaningfully
    # extends this crop's shelf life. Storing a highly perishable crop with
    # no real cold-chain benefit just delays the loss and adds a cost.
    if remaining > 0.01:
        worth_storing = profile.shelf_life_cold_storage_days > profile.shelf_life_ambient_days * 1.5
        if worth_storing:
            for dist_km, facility in _nearby_storage(db, crop_type, latitude, longitude, radius_km):
                if remaining <= 0.01:
                    break
                take = min(remaining, facility.available_capacity_kg)
                if take <= 0:
                    continue
                value = take * sell_price if sell_price else None
                cost = take * facility.cost_per_kg_per_day
                total_cost += cost
                if value is not None:
                    gross_value += value
                    any_value_computed = True
                allocations.append(ChannelAllocation(
                    channel="store", quantity_kg=round(take, 1),
                    unit_price_per_kg=sell_price,
                    estimated_value=round(value, 2) if value is not None else None,
                    facility_name=facility.name, facility_id=facility.id,
                    distance_km=round(dist_km, 1),
                    note=(
                        f"Cold-store at {facility.name} ({dist_km:.1f} km) — "
                        f"\u20b9{facility.cost_per_kg_per_day:.2f}/kg/day, safe for up to "
                        f"{profile.shelf_life_cold_storage_days:.0f} days there."
                    ),
                ))
                remaining -= take
        else:
            reasoning.append(
                f"Cold storage wouldn't meaningfully extend {crop_type}'s shelf life "
                f"(ambient {profile.shelf_life_ambient_days:.0f}d vs cold-stored "
                f"{profile.shelf_life_cold_storage_days:.0f}d) — skipped in favor of processing."
            )

    # 3. Process — route whatever's left to the best-paying nearby unit
    # that accepts this crop. Usually the right place for surplus a
    # perishable crop can't be sold or stored in time.
    if remaining > 0.01:
        for dist_km, unit in _nearby_processing(db, crop_type, latitude, longitude, radius_km):
            if remaining <= 0.01:
                break
            take = min(remaining, unit.remaining_intake_today_kg)
            if take <= 0:
                continue
            value = take * unit.price_per_kg
            gross_value += value
            any_value_computed = True
            allocations.append(ChannelAllocation(
                channel="process", quantity_kg=round(take, 1),
                unit_price_per_kg=unit.price_per_kg,
                estimated_value=round(value, 2),
                facility_name=unit.name, facility_id=unit.id,
                distance_km=round(dist_km, 1),
                note=(
                    f"Send to {unit.name} ({dist_km:.1f} km) for "
                    f"{unit.output_product or 'processing'} at \u20b9{unit.price_per_kg:.2f}/kg."
                ),
            ))
            remaining -= take

    # 4. Anything still unallocated is genuinely at risk — say so plainly
    # instead of quietly assuming it gets sold somehow.
    if remaining > 0.01:
        allocations.append(ChannelAllocation(
            channel="at_risk", quantity_kg=round(remaining, 1),
            note=(
                "No market, storage, or processing capacity found for this quantity "
                f"within {radius_km:.0f} km today. A distress sale, community/NGO donation, "
                "or on-farm composting will likely recover more value than a total loss."
            ),
        ))
        reasoning.append(
            f"{remaining:.0f} kg has nowhere to go today within {radius_km:.0f} km — "
            "flagged at-risk rather than silently dropped."
        )

    expected_net_value = round(gross_value - total_cost, 2) if any_value_computed else None

    # Baseline: what a farmer gets with no plan at all — sell what the
    # market absorbs at fair price, and the rest at a steep same-day
    # distress discount (see Settings docstring). This is the realistic
    # "do nothing" comparison, not an idealized full-price sale.
    baseline_value: Optional[float] = None
    if sell_price is not None:
        sellable_now = min(quantity_kg, daily_demand)
        forced_distress = max(0.0, quantity_kg - daily_demand)
        baseline_value = round(
            sellable_now * sell_price
            + forced_distress * sell_price * settings.POST_HARVEST_DISTRESS_SALE_FRACTION,
            2,
        )

    projected_savings = (
        round(expected_net_value - baseline_value, 2)
        if expected_net_value is not None and baseline_value is not None
        else None
    )

    return RecommendationResult(
        crop_type=crop_type,
        quantity_kg=quantity_kg,
        perishability_tier=profile.tier,
        allocations=allocations,
        wholesale_price_per_kg=price_row.wholesale_price_per_kg if price_row else None,
        expected_net_value=expected_net_value,
        baseline_sell_all_today_value=baseline_value,
        projected_savings=projected_savings,
        reasoning=reasoning,
    )
