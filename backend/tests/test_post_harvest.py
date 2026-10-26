from datetime import datetime, timezone

import pytest

from app.models import MarketPrice, ProcessingUnit, StorageFacility
from app.services.post_harvest_advisor import recommend_allocation


def _seed_price(db_session, crop_type, district, wholesale, retail=None):
    db_session.add(MarketPrice(
        crop_type=crop_type, market_name="Test Mandi", district=district,
        wholesale_price_per_kg=wholesale, retail_price_per_kg=retail,
        source="manual", recorded_date=datetime.now(timezone.utc),
    ))
    db_session.commit()


def _channels(result):
    return {a.channel: a.quantity_kg for a in result.allocations}


# ---------- Service-level tests ----------

def test_no_demand_history_uses_conservative_default_and_flags_the_rest_at_risk(db_session):
    _seed_price(db_session, "onion", "TestDistrictA", wholesale=10.0, retail=20.0)
    result = recommend_allocation(
        db_session, crop_type="onion", quantity_kg=100,
        district="TestDistrictA", latitude=11.0, longitude=77.0,
    )
    channels = _channels(result)
    # No order history yet -> 40% of the lot sold now (Settings default);
    # no storage/processing facilities seeded for onion in this test -> rest is at risk.
    assert channels["sell_now"] == pytest.approx(40.0)
    assert channels["at_risk"] == pytest.approx(60.0)
    assert result.wholesale_price_per_kg == pytest.approx(10.0)


def test_storage_and_processing_absorb_the_remainder(db_session):
    _seed_price(db_session, "tomato", "TestDistrictB", wholesale=15.0, retail=30.0)
    db_session.add(StorageFacility(
        name="Test Cold Store", district="TestDistrictB", latitude=11.0, longitude=77.0,
        capacity_kg=200, available_capacity_kg=200, cost_per_kg_per_day=0.5,
        supported_crop_types="tomato",
    ))
    db_session.add(ProcessingUnit(
        name="Test Puree Unit", district="TestDistrictB", latitude=11.01, longitude=77.01,
        output_product="tomato puree", daily_intake_capacity_kg=500,
        remaining_intake_today_kg=500, price_per_kg=8.0, accepted_crop_types="tomato",
    ))
    db_session.commit()

    result = recommend_allocation(
        db_session, crop_type="tomato", quantity_kg=500,
        district="TestDistrictB", latitude=11.0, longitude=77.0,
    )
    channels = _channels(result)
    assert "at_risk" not in channels
    assert channels["sell_now"] == pytest.approx(200.0)   # 40% no-history default
    assert channels["store"] == pytest.approx(200.0)      # fills the one facility
    assert channels["process"] == pytest.approx(100.0)    # whatever's left
    assert result.expected_net_value is not None
    assert result.projected_savings is not None


def test_durable_crop_skips_storage_channel(db_session):
    # Cold storage barely extends paddy's already-long shelf life, so the
    # advisor should skip it even with a facility available.
    db_session.add(StorageFacility(
        name="Test Grain Store", district="TestDistrictC", latitude=11.0, longitude=77.0,
        capacity_kg=1000, available_capacity_kg=1000, cost_per_kg_per_day=0.1,
        supported_crop_types="paddy",
    ))
    db_session.commit()
    result = recommend_allocation(
        db_session, crop_type="paddy", quantity_kg=300,
        district="TestDistrictC", latitude=11.0, longitude=77.0,
    )
    assert "store" not in _channels(result)
    assert any("wouldn't meaningfully extend" in line for line in result.reasoning)


def test_facility_outside_radius_is_ignored(db_session):
    db_session.add(StorageFacility(
        name="Far Away Store", district="TestDistrictD", latitude=30.0, longitude=90.0,
        capacity_kg=1000, available_capacity_kg=1000, cost_per_kg_per_day=0.2,
        supported_crop_types="brinjal",
    ))
    db_session.commit()
    result = recommend_allocation(
        db_session, crop_type="brinjal", quantity_kg=40,
        district="TestDistrictD", latitude=11.0, longitude=77.0, radius_km=50.0,
    )
    assert "store" not in _channels(result)


def test_no_price_data_still_returns_a_full_quantity_split(db_session):
    result = recommend_allocation(
        db_session, crop_type="banana", quantity_kg=50,
        district="NoDataDistrict", latitude=11.0, longitude=77.0,
    )
    assert result.wholesale_price_per_kg is None
    assert result.expected_net_value is None
    assert sum(a.quantity_kg for a in result.allocations) == pytest.approx(50.0)


def test_rejects_non_positive_quantity(db_session):
    with pytest.raises(ValueError):
        recommend_allocation(
            db_session, crop_type="tomato", quantity_kg=0,
            district="X", latitude=11.0, longitude=77.0,
        )


# ---------- API-level tests ----------

def _register_and_login(client, phone, role="farmer"):
    client.post("/auth/register", json={
        "full_name": "Post Harvest Test User", "phone_number": phone,
        "password": "secret123", "role": role, "district": "TestDistrictE",
    })
    resp = client.post("/auth/login", data={"username": phone, "password": "secret123"})
    return resp.json()["access_token"]


def test_recommend_endpoint_requires_farmer_role(client):
    token = _register_and_login(client, "+919444444001", role="buyer")
    resp = client.post(
        "/post-harvest/recommend",
        json={"crop_type": "tomato", "quantity_kg": 50, "district": "TestDistrictE",
              "latitude": 11.0, "longitude": 77.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_recommend_endpoint_returns_allocation_and_is_logged_to_history(client):
    token = _register_and_login(client, "+919444444002", role="farmer")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/post-harvest/recommend",
        json={"crop_type": "tomato", "quantity_kg": 50, "district": "TestDistrictE",
              "latitude": 11.0, "longitude": 77.0},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["crop_type"] == "tomato"
    assert sum(a["quantity_kg"] for a in body["allocations"]) == pytest.approx(50.0)

    resp = client.get("/post-harvest/history", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["crop_type"] == "tomato"


def test_storage_facility_onboarding_is_admin_only(client):
    farmer_token = _register_and_login(client, "+919444444003", role="farmer")
    payload = {
        "name": "New Cold Store", "district": "TestDistrictE",
        "latitude": 11.0, "longitude": 77.0, "capacity_kg": 500,
        "available_capacity_kg": 500, "cost_per_kg_per_day": 0.4,
        "supported_crop_types": "tomato,onion",
    }
    resp = client.post(
        "/post-harvest/storage-facilities", json=payload,
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    assert resp.status_code == 403

    admin_token = _register_and_login(client, "+919444444004", role="admin")
    resp = client.post(
        "/post-harvest/storage-facilities", json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201, resp.text

    resp = client.get("/post-harvest/storage-facilities", params={"district": "TestDistrictE"})
    assert resp.status_code == 200
    assert any(f["name"] == "New Cold Store" for f in resp.json())
