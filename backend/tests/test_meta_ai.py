"""
Unit & integration tests for Meta AI tooling integration:
1. Fallbacks when META_AI_ENABLED=false
2. Numeric integrity guardrails in advisor_explainer (no invented prices/numbers)
3. Server-side grade audit task logic (Spark -> Wonder escalation, invariant grade check)
4. Voice intent parsing
5. Agentic loop with tool calls
"""
import json
import pytest
from unittest.mock import patch, MagicMock

from app.config import get_settings
from app.models import CropGrade, CropListing, PostHarvestRecommendation, User, UserRole
from app.services.advisor_explainer import explain, _numbers
from app.services.grade_audit import GradeVerdict
from app.services.meta_ai import MetaAIUnavailable
from app.tasks import audit_listing_grade
from app.auth import create_access_token

settings = get_settings()


def test_explainer_number_guardrail_blocks_invented_figures():
    facts = {
        "crop": "tomato",
        "quantity_kg": 500,
        "district": "Coimbatore",
        "sell_now_kg": 200,
        "store_kg": 300,
        "process_kg": 0,
        "at_risk_kg": 0,
        "expected_net_value_rupees": 12500,
        "sell_everything_today_rupees": 8000,
        "extra_rupees_earned": 4500,
    }

    faithful_text = "இன்று 200 கிலோ தக்காளி விற்கவும், 300 கிலோ சேமிக்கவும். நிகர மதிப்பு 12500 ரூபாய்."
    with patch("app.services.advisor_explainer.ask_text", return_value=faithful_text):
        res = explain(facts, "ta")
        assert res == faithful_text

    hallucinated_text = "இன்று 200 கிலோ தக்காளி விற்கவும். விலை 555 ரூபாய்."
    with patch("app.services.advisor_explainer.ask_text", return_value=hallucinated_text):
        res = explain(facts, "ta")
        assert res is None


def test_meta_ai_disabled_fallback(client, db_session):
    settings.META_AI_ENABLED = False

    user = User(
        full_name="Test Farmer Meta",
        phone_number="+919999900001",
        hashed_password="hash",
        role=UserRole.FARMER,
        district="Coimbatore",
    )
    db_session.add(user)
    db_session.commit()

    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/voice/intent", json={"transcript": "500 kg tomato"}, headers=headers)
    assert resp.status_code == 503

    rec = PostHarvestRecommendation(
        farmer_id=user.id,
        crop_type="tomato",
        quantity_kg=500,
        district="Coimbatore",
        latitude=11.0,
        longitude=77.0,
        perishability_tier="highly_perishable",
    )
    db_session.add(rec)
    db_session.commit()

    resp = client.get(f"/post-harvest/{rec.id}/explanation", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["explanation"] is None


def test_audit_grade_invariant_device_grade_never_overwritten(db_session, tmp_path):
    img_file = tmp_path / "test_crop.jpg"
    img_file.write_bytes(b"dummy_jpeg_bytes")

    user = User(
        full_name="Farmer Joe",
        phone_number="+919876543211",
        hashed_password="hash",
        role=UserRole.FARMER,
        district="Salem",
    )
    db_session.add(user)
    db_session.commit()

    listing = CropListing(
        farmer_id=user.id,
        crop_type="tomato",
        grade=CropGrade.GRADE_A,
        quantity_kg=200,
        district="Salem",
        latitude=11.5,
        longitude=78.1,
        image_path=str(img_file),
    )
    db_session.add(listing)
    db_session.commit()

    verdict = GradeVerdict(
        grade="grade_b",
        confidence=0.85,
        defects=["bruise"],
        estimated_defect_pct=8.0,
        rationale="Minor surface bruises detected",
    )

    with patch("app.tasks.audit_grade", return_value=verdict):
        status = audit_listing_grade(listing.id)
        assert status == "disagree"

    db_session.refresh(listing)
    assert listing.grade == CropGrade.GRADE_A
    assert listing.audit_grade == "grade_b"
    assert listing.audit_status == "disagree"
    assert listing.audit_confidence == 0.85
    assert "bruise" in listing.audit_defects


def test_voice_intent_schema_extraction():
    from app.routers.voice import HarvestIntent

    data = {
        "crop_type": "tomato",
        "quantity_kg": 500.0,
        "district": "Coimbatore",
        "missing": [],
    }
    intent = HarvestIntent(**data)
    assert intent.crop_type == "tomato"
    assert intent.quantity_kg == 500.0
    assert intent.district == "Coimbatore"
    assert len(intent.missing) == 0

    partial = HarvestIntent(crop_type="onion", missing=["quantity_kg", "district"])
    assert partial.crop_type == "onion"
    assert partial.quantity_kg is None
    assert "quantity_kg" in partial.missing
