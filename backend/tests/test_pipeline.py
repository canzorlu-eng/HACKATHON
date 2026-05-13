"""
Tests for the LangGraph AI pipeline.

MockAIClient is used throughout — Gemini is never called.
Tests cover:
  - Individual node functions (unit)
  - Full pipeline (integration, no network)
  - API endpoint via TestClient (end-to-end with mock)
"""

import asyncio
import pytest
from tests.conftest import JPEG_BYTES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """Run an async coroutine in the test suite synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _base_state(**overrides) -> dict:
    base = {
        "analysis_id":     "aaaaaaaa-0000-0000-0000-000000000001",
        "user_id":         "bbbbbbbb-0000-0000-0000-000000000001",
        "height_cm":       175,
        "weight_kg":       70,
        "fit_preference":  "regular",
        "body_image_ref":  None,
        "garment_image_ref": "garment/test.jpg",
        "storage_dir":     "/tmp/test",
        "intent_valid":    False,
        "intent_error":    None,
        "body_analysis":   None,
        "garment_analysis": None,
        "review_insights": [],
        "recommendation":  None,
        "risk_evaluation": None,
        "final_response":  None,
        "pipeline_error":  None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Node unit tests
# ---------------------------------------------------------------------------

class TestIntentValidator:
    from app.ai.nodes import intent_validator_node

    def test_valid_state_passes(self):
        from app.ai.nodes import intent_validator_node
        result = intent_validator_node(_base_state())
        assert result["intent_valid"] is True
        assert result["intent_error"] is None

    def test_missing_garment_ref_fails(self):
        from app.ai.nodes import intent_validator_node
        result = intent_validator_node(_base_state(garment_image_ref=""))
        assert result["intent_valid"] is False
        assert result["intent_error"]

    def test_invalid_height_fails(self):
        from app.ai.nodes import intent_validator_node
        result = intent_validator_node(_base_state(height_cm=10))
        assert result["intent_valid"] is False

    def test_invalid_weight_fails(self):
        from app.ai.nodes import intent_validator_node
        result = intent_validator_node(_base_state(weight_kg=5))
        assert result["intent_valid"] is False


class TestMockAIClient:
    def test_analyze_body_with_image(self):
        from app.ai.client import MockAIClient
        result = _run(MockAIClient().analyze_body(b"fake", 175, 70, "regular"))
        assert "fit_tendency" in result
        assert "confidence" in result
        assert result["confidence"] >= 0.7

    def test_analyze_body_no_image_lower_confidence(self):
        from app.ai.client import MockAIClient
        result = _run(MockAIClient().analyze_body(None, 175, 70, "regular"))
        assert result["confidence"] < 0.7

    def test_analyze_garment(self):
        from app.ai.client import MockAIClient
        result = _run(MockAIClient().analyze_garment(b"fake"))
        assert "fit_type" in result
        assert "confidence" in result
        assert result["confidence"] > 0


class TestRecommendationGenerator:
    def test_returns_valid_size(self):
        from app.ai.nodes import recommendation_generator_node
        state = _base_state(
            body_analysis={"fit_tendency": "standart", "confidence": 0.75, "uncertainty_reason": ""},
            garment_analysis={"fit_type": "regular", "brand_sizing_tendency": "standart", "confidence": 0.80, "uncertainty_reason": ""},
            review_insights=[],
        )
        result = recommendation_generator_node(state)
        rec = result["recommendation"]
        assert rec["recommended_size"] in ("XS", "S", "M", "L", "XL", "XXL")
        assert 0.0 < rec["confidence"] <= 1.0
        assert rec["explanation_tr"]
        assert rec["uncertainty_tr"]

    def test_confidence_lower_without_body_image(self):
        from app.ai.nodes import recommendation_generator_node
        state_with = _base_state(
            body_image_ref="body/photo.jpg",
            body_analysis={"fit_tendency": "standart", "confidence": 0.75, "uncertainty_reason": ""},
            garment_analysis={"fit_type": "regular", "brand_sizing_tendency": "standart", "confidence": 0.80, "uncertainty_reason": ""},
        )
        state_without = _base_state(
            body_image_ref=None,
            body_analysis={"fit_tendency": "standart", "confidence": 0.75, "uncertainty_reason": ""},
            garment_analysis={"fit_type": "regular", "brand_sizing_tendency": "standart", "confidence": 0.80, "uncertainty_reason": ""},
        )
        with_conf = recommendation_generator_node(state_with)["recommendation"]["confidence"]
        without_conf = recommendation_generator_node(state_without)["recommendation"]["confidence"]
        assert with_conf > without_conf

    def test_small_brand_shifts_size_up(self):
        from app.ai.nodes import recommendation_generator_node
        base_state = _base_state(
            height_cm=175, weight_kg=70,
            body_analysis={"fit_tendency": "standart", "confidence": 0.75, "uncertainty_reason": ""},
        )
        standard = dict(base_state, garment_analysis={"fit_type": "regular", "brand_sizing_tendency": "standart", "confidence": 0.80, "uncertainty_reason": ""})
        small    = dict(base_state, garment_analysis={"fit_type": "regular", "brand_sizing_tendency": "küçük kalıplı", "confidence": 0.80, "uncertainty_reason": ""})
        sizes = ("XS", "S", "M", "L", "XL", "XXL")
        std_i   = sizes.index(recommendation_generator_node(standard)["recommendation"]["recommended_size"])
        small_i = sizes.index(recommendation_generator_node(small)["recommendation"]["recommended_size"])
        assert small_i >= std_i  # small brand → same or larger size


class TestRiskEvaluator:
    def _rec(self, conf=0.75):
        return {"recommended_size": "M", "confidence": conf, "explanation_tr": "", "uncertainty_tr": ""}

    def test_low_confidence_produces_medium_or_high_risk(self):
        from app.ai.nodes import risk_evaluator_node
        state = _base_state(
            recommendation=self._rec(conf=0.35),
            garment_analysis={"fit_type": "regular", "fabric_cues": "", "brand_sizing_tendency": "standart"},
            review_insights=[],
        )
        result = risk_evaluator_node(state)
        assert result["risk_evaluation"]["risk_level"] in ("medium", "high")

    def test_high_confidence_low_risk(self):
        from app.ai.nodes import risk_evaluator_node
        state = _base_state(
            body_image_ref="body/photo.jpg",
            recommendation=self._rec(conf=0.90),
            garment_analysis={"fit_type": "regular", "fabric_cues": "ağır kumaş", "brand_sizing_tendency": "standart"},
            review_insights=[],
        )
        result = risk_evaluator_node(state)
        assert result["risk_evaluation"]["risk_level"] == "low"

    def test_no_body_image_adds_risk_factor(self):
        from app.ai.nodes import risk_evaluator_node
        state = _base_state(
            body_image_ref=None,
            recommendation=self._rec(conf=0.80),
            garment_analysis={"fit_type": "regular", "fabric_cues": "", "brand_sizing_tendency": "standart"},
            review_insights=[],
        )
        result = risk_evaluator_node(state)
        risk_factors = result["risk_evaluation"]["risk_factors"]
        assert any("fotoğraf" in f.lower() for f in risk_factors)

    def test_result_has_required_fields(self):
        from app.ai.nodes import risk_evaluator_node
        state = _base_state(
            recommendation=self._rec(),
            garment_analysis={"fit_type": "regular", "fabric_cues": "", "brand_sizing_tendency": "standart"},
        )
        ev = risk_evaluator_node(state)["risk_evaluation"]
        for key in ("risk_level", "risk_level_tr", "risk_factors", "risk_score", "confidence"):
            assert key in ev


class TestTurkishFormatter:
    def test_output_has_all_required_fields(self):
        from app.ai.nodes import turkish_formatter_node
        state = _base_state(
            recommendation={"recommended_size": "L", "confidence": 0.82, "explanation_tr": "Açıklama", "uncertainty_tr": "Belirsizlik"},
            risk_evaluation={"risk_level": "low", "risk_level_tr": "Düşük Risk", "risk_factors": [], "risk_score": 0.2, "confidence": 0.82},
            review_insights=[{"theme": "kaliteli kumaş", "count": 5, "sentiment": "positive"}],
        )
        result = turkish_formatter_node(state)["final_response"]
        assert result["recommended_size"] == "L"
        assert result["confidence_score"] == 0.82
        assert result["confidence_pct"] == "%82"
        assert result["explanation_tr"] == "Açıklama"
        assert result["risk_level"] == "low"
        assert result["risk_level_tr"] == "Düşük Risk"
        assert isinstance(result["risk_factors_tr"], list)
        assert result["uncertainty_tr"] == "Belirsizlik"
        assert isinstance(result["community_insights_tr"], list)
        assert result["community_insights_tr"]

    def test_fallback_community_insight_when_empty(self):
        from app.ai.nodes import turkish_formatter_node
        state = _base_state(
            recommendation={"recommended_size": "M", "confidence": 0.70, "explanation_tr": "", "uncertainty_tr": ""},
            risk_evaluation={"risk_level": "medium", "risk_level_tr": "Orta Risk", "risk_factors": [], "risk_score": 0.4, "confidence": 0.70},
            review_insights=[],
        )
        result = turkish_formatter_node(state)["final_response"]
        assert len(result["community_insights_tr"]) == 1
        assert "yeterli" in result["community_insights_tr"][0].lower()


# ---------------------------------------------------------------------------
# Full pipeline integration tests (MockAIClient, no file I/O)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pipeline_invalid_intent_stops_early():
    from app.ai.client import MockAIClient
    from app.ai.graph import build_pipeline
    pipeline = build_pipeline(MockAIClient())
    state = _base_state(garment_image_ref="")  # missing garment ref
    result = await pipeline.ainvoke(state)
    assert result.get("intent_valid") is False
    assert result.get("final_response") is None


@pytest.mark.asyncio
async def test_pipeline_full_run_returns_required_fields(tmp_path):
    """End-to-end pipeline with real file I/O via tmp_path."""
    from app.ai.client import MockAIClient
    from app.ai.graph import build_pipeline

    # Write a fake garment image so read_image_bytes finds it
    (tmp_path / "garment").mkdir(parents=True)
    img_path = tmp_path / "garment" / "test.jpg"
    img_path.write_bytes(JPEG_BYTES)

    pipeline = build_pipeline(MockAIClient())
    state = _base_state(
        garment_image_ref="garment/test.jpg",
        storage_dir=str(tmp_path),
    )
    result = await pipeline.ainvoke(state)

    assert result.get("intent_valid") is True
    assert result.get("body_analysis") is not None
    assert result.get("garment_analysis") is not None
    assert result.get("review_insights") is not None
    assert result.get("recommendation") is not None
    assert result.get("risk_evaluation") is not None

    fr = result.get("final_response")
    assert fr is not None
    for field in (
        "recommended_size",
        "confidence_score",
        "confidence_pct",
        "explanation_tr",
        "risk_level",
        "risk_level_tr",
        "risk_factors_tr",
        "uncertainty_tr",
        "community_insights_tr",
    ):
        assert field in fr, f"Missing field in final_response: {field}"

    assert fr["recommended_size"] in ("XS", "S", "M", "L", "XL", "XXL")
    assert 0.0 < fr["confidence_score"] <= 1.0
    assert fr["confidence_pct"].startswith("%")
    assert fr["risk_level"] in ("low", "medium", "high")


@pytest.mark.asyncio
async def test_pipeline_no_body_image_still_completes(tmp_path):
    from app.ai.client import MockAIClient
    from app.ai.graph import build_pipeline

    (tmp_path / "garment").mkdir(parents=True)
    (tmp_path / "garment" / "test.jpg").write_bytes(JPEG_BYTES)

    pipeline = build_pipeline(MockAIClient())
    state = _base_state(
        body_image_ref=None,
        garment_image_ref="garment/test.jpg",
        storage_dir=str(tmp_path),
    )
    result = await pipeline.ainvoke(state)
    assert result["final_response"] is not None
    # No body image → lower confidence
    assert result["final_response"]["confidence_score"] < 0.80


# ---------------------------------------------------------------------------
# API endpoint integration tests
# ---------------------------------------------------------------------------

def _create_user(client):
    r = client.post(
        "/api/v1/profile",
        data={"height_cm": "175", "weight_kg": "70", "fit_preference": "regular"},
    )
    assert r.status_code == 201
    return r.json()["user_id"]


def test_api_analyze_returns_ai_fields(client):
    uid = _create_user(client)
    r = client.post(
        "/api/v1/analyze",
        data={"user_id": uid},
        files={"garment_image": ("shirt.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert r.status_code == 202
    body = r.json()
    # Core fields still present
    assert "analysis_id" in body
    assert body["garment_image_ref"].startswith("garment/")
    assert "Görsel doğrulandı" in body["message"]
    # AI fields populated by mock pipeline
    assert body["recommended_size"] in ("XS", "S", "M", "L", "XL", "XXL")
    assert body["confidence_score"] is not None
    assert body["confidence_pct"].startswith("%")
    assert body["explanation_tr"]
    assert body["risk_level"] in ("low", "medium", "high")
    assert body["risk_level_tr"]
    assert isinstance(body["risk_factors_tr"], list)
    assert body["uncertainty_tr"] is not None
    assert isinstance(body["community_insights_tr"], list)


def test_api_analyze_stores_result_in_history(client):
    uid = _create_user(client)
    upload = client.post(
        "/api/v1/analyze",
        data={"user_id": uid},
        files={"garment_image": ("shirt.jpg", JPEG_BYTES, "image/jpeg")},
    ).json()

    r = client.get(f"/api/v1/history/{uid}/{upload['analysis_id']}")
    assert r.status_code == 200
    detail = r.json()
    assert detail["recommended_size"] == upload["recommended_size"]
    assert detail["risk_level"] == upload["risk_level"]
    fr = detail["formatted_response"]
    assert fr["confidence_score"] == upload["confidence_score"]
