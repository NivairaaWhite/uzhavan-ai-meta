"""
Fair Price Engine.

The source blueprint referenced a "Price Algorithm" without specifying its
formula, so this is an explicit, documented design (tunable via Settings,
not hard-coded), not a literal transcription of anything:

  fair_price = wholesale + farmer_share * (retail - wholesale)
  fair_price = fair_price * (1 - platform_fee_pct)

Rationale: the farmer should get more than the wholesale mandi floor
(middlemen currently capture most of the wholesale->retail spread), but
the platform can't promise retail price (it has no retail overhead, but
it does have logistics/spoilage/collection costs) — so `farmer_share`
splits the spread, and a small flat platform fee funds the escrow/
logistics/ops layer. Every number is a Settings field so it can be
re-tuned per crop or region without a code change.
"""
from dataclasses import dataclass
from typing import Optional

from app.config import get_settings

settings = get_settings()


@dataclass
class FairPriceResult:
    wholesale_price_per_kg: float
    retail_price_per_kg: Optional[float]
    fair_price_per_kg: float
    farmer_share_pct: float


def compute_fair_price(
    wholesale_price_per_kg: float,
    retail_price_per_kg: Optional[float] = None,
    farmer_share: Optional[float] = None,
    platform_fee_pct: Optional[float] = None,
) -> FairPriceResult:
    if wholesale_price_per_kg <= 0:
        raise ValueError("wholesale_price_per_kg must be positive")

    farmer_share = settings.PRICE_FARMER_SHARE if farmer_share is None else farmer_share
    platform_fee_pct = (
        settings.PRICE_PLATFORM_FEE_PCT if platform_fee_pct is None else platform_fee_pct
    )
    if not (0 <= farmer_share <= 1):
        raise ValueError("farmer_share must be between 0 and 1")
    if not (0 <= platform_fee_pct < 1):
        raise ValueError("platform_fee_pct must be between 0 and 1")

    if retail_price_per_kg is None or retail_price_per_kg <= wholesale_price_per_kg:
        # No usable retail signal (or a bad/stale scrape) — fall back to a
        # small guaranteed premium over the wholesale floor rather than
        # trusting a broken spread.
        base = wholesale_price_per_kg * 1.05
    else:
        spread = retail_price_per_kg - wholesale_price_per_kg
        base = wholesale_price_per_kg + farmer_share * spread

    fair_price = round(base * (1 - platform_fee_pct), 2)

    return FairPriceResult(
        wholesale_price_per_kg=wholesale_price_per_kg,
        retail_price_per_kg=retail_price_per_kg,
        fair_price_per_kg=fair_price,
        farmer_share_pct=farmer_share,
    )
