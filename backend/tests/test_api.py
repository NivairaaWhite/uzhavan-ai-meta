def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_and_login_flow(client):
    resp = client.post("/auth/register", json={
        "full_name": "Test Farmer",
        "phone_number": "+919876543210",
        "password": "secret123",
        "role": "farmer",
        "preferred_language": "ta",
        "district": "Coimbatore",
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["phone_number"] == "+919876543210"
    assert body["kyc_status"] == "unverified"

    resp = client.post("/auth/login", data={
        "username": "+919876543210", "password": "secret123",
    })
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]

    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Test Farmer"


def test_duplicate_phone_number_rejected(client):
    payload = {
        "full_name": "Dup", "phone_number": "+919000000001",
        "password": "secret123", "role": "farmer",
    }
    assert client.post("/auth/register", json=payload).status_code == 201
    assert client.post("/auth/register", json=payload).status_code == 409


def _farmer_token(client, phone="+919111111111"):
    client.post("/auth/register", json={
        "full_name": "Farmer B", "phone_number": phone,
        "password": "secret123", "role": "farmer",
    })
    resp = client.post("/auth/login", data={"username": phone, "password": "secret123"})
    return resp.json()["access_token"]


def test_create_and_list_crop_listing(client):
    token = _farmer_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/crop-listings", json={
        "crop_type": "tomato",
        "grade": "grade_a",
        "grade_confidence": 0.92,
        "quantity_kg": 250,
        "target_price_per_kg": 18.5,
        "latitude": 11.0168,
        "longitude": 76.9558,
    }, headers=headers)
    assert resp.status_code == 201, resp.text
    listing_id = resp.json()["id"]

    resp = client.get("/crop-listings", params={"crop_type": "tomato"})
    assert resp.status_code == 200
    assert any(l["id"] == listing_id for l in resp.json())


def test_offline_bulk_sync_is_idempotent(client):
    token = _farmer_token(client, phone="+919222222222")
    headers = {"Authorization": f"Bearer {token}"}
    body = {"listings": [{
        "crop_type": "onion", "grade": "grade_b", "quantity_kg": 100,
        "latitude": 11.0, "longitude": 77.0, "offline_scan_uuid": "device-uuid-123",
    }]}
    r1 = client.post("/crop-listings/sync", json=body, headers=headers)
    assert r1.status_code == 200
    assert len(r1.json()) == 1
    first_id = r1.json()[0]["id"]

    # Simulate the phone retrying the same sync after a dropped connection
    r2 = client.post("/crop-listings/sync", json=body, headers=headers)
    assert r2.status_code == 200
    assert r2.json()[0]["id"] == first_id  # no duplicate created


def test_buyer_only_role_enforced_on_orders(client):
    token = _farmer_token(client, phone="+919333333333")
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/orders", json={"listing_id": "does-not-matter", "quantity_kg": 10}, headers=headers)
    assert resp.status_code == 403  # farmers cannot place buy orders


def test_fair_price_404_when_no_market_data(client):
    resp = client.get("/market/fair-price", params={"crop_type": "dragonfruit", "district": "Nowhere"})
    assert resp.status_code == 404
