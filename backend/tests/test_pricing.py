import pytest

from app.services.pricing import compute_fair_price


def test_fair_price_splits_the_spread():
    result = compute_fair_price(wholesale_price_per_kg=20.0, retail_price_per_kg=40.0)
    # base = 20 + 0.65*(40-20) = 33; fair = 33 * (1-0.03) = 32.01
    assert result.fair_price_per_kg == pytest.approx(32.01, abs=0.01)
    assert result.fair_price_per_kg > result.wholesale_price_per_kg
    assert result.fair_price_per_kg < result.retail_price_per_kg


def test_fair_price_without_retail_signal_falls_back_to_premium():
    result = compute_fair_price(wholesale_price_per_kg=20.0, retail_price_per_kg=None)
    # base = 20 * 1.05 = 21; fair = 21 * 0.97 = 20.37
    assert result.fair_price_per_kg == pytest.approx(20.37, abs=0.01)


def test_fair_price_rejects_bad_retail_signal():
    # retail <= wholesale is a broken/stale scrape, not a real spread
    result = compute_fair_price(wholesale_price_per_kg=20.0, retail_price_per_kg=15.0)
    assert result.fair_price_per_kg == pytest.approx(20.37, abs=0.01)


def test_fair_price_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        compute_fair_price(wholesale_price_per_kg=0)
    with pytest.raises(ValueError):
        compute_fair_price(wholesale_price_per_kg=10, farmer_share=1.5)


def test_custom_weights_are_respected():
    result = compute_fair_price(
        wholesale_price_per_kg=10.0, retail_price_per_kg=30.0,
        farmer_share=1.0, platform_fee_pct=0.0,
    )
    assert result.fair_price_per_kg == pytest.approx(30.0)
