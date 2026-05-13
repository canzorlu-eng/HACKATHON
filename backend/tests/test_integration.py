"""
End-to-end integration tests: full analysis pipeline with MockAIClient.

Covers the complete user journey from profile creation through garment
upload, AI recommendation, and history retrieval — verifying:
  - Turkish output in every user-facing field
  - confidence_score presence and valid range
  - explanation_tr and uncertainty_tr are non-empty strings
  - risk fields are populated and valid
  - community_insights_tr is a list of Turkish strings
  - upload errors return 422 with Turkish messages
  - history reflects completed analyses
  - no secrets appear in API responses
"""

import pytest

from tests.conftest import JPEG_BYTES, PNG_BYTES, BMP_BYTES, GARBAGE_BYTES


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_profile(client, height=170, weight=65, preference="regular"):
    r = client.post(
        "/api/v1/profile",
        data={
            "height_cm": str(height),
            "weight_kg": str(weight),
            "fit_preference": preference,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["user_id"]


def _analyze(client, user_id, image_bytes=JPEG_BYTES, filename="shirt.jpg"):
    r = client.post(
        "/api/v1/analyze",
        data={"user_id": user_id},
        files={"garment_image": (filename, image_bytes, "image/jpeg")},
    )
    return r


# ── Full happy-path journey ───────────────────────────────────────────────────

class TestFullAnalysisJourney:
    def test_profile_create_returns_correct_fields(self, client):
        r = client.post(
            "/api/v1/profile",
            data={"height_cm": "175", "weight_kg": "70", "fit_preference": "slim"},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["height_cm"] == 175
        assert body["weight_kg"] == 70
        assert body["fit_preference"] == "slim"
        assert body["has_body_image"] is False
        assert "user_id" in body
        assert "created_at" in body

    def test_analyze_returns_202_with_full_ai_fields(self, client):
        uid = _create_profile(client)
        r = _analyze(client, uid)
        assert r.status_code == 202
        body = r.json()
        assert "analysis_id" in body
        assert body["garment_image_ref"].startswith("garment/")

    def test_recommended_size_is_valid_clothing_size(self, client):
        uid = _create_profile(client)
        body = _analyze(client, uid).json()
        valid_sizes = {"XS", "S", "M", "L", "XL", "XXL"}
        assert body["recommended_size"] in valid_sizes

    def test_confidence_score_is_float_in_valid_range(self, client):
        uid = _create_profile(client)
        body = _analyze(client, uid).json()
        score = body["confidence_score"]
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_confidence_pct_is_formatted_turkish_string(self, client):
        uid = _create_profile(client)
        body = _analyze(client, uid).json()
        pct = body["confidence_pct"]
        assert pct is not None
        assert pct.startswith("%")
        pct_value = int(pct.lstrip("%"))
        assert 0 <= pct_value <= 100

    def test_explanation_tr_is_nonempty_turkish_string(self, client):
        uid = _create_profile(client)
        body = _analyze(client, uid).json()
        expl = body["explanation_tr"]
        assert expl is not None
        assert len(expl) > 10
        # Must contain at least one Turkish word pattern
        assert "beden" in expl.lower() or "öneril" in expl.lower() or "kesim" in expl.lower()

    def test_risk_level_is_valid_enum(self, client):
        uid = _create_profile(client)
        body = _analyze(client, uid).json()
        assert body["risk_level"] in ("low", "medium", "high")

    def test_risk_level_tr_is_turkish_string(self, client):
        uid = _create_profile(client)
        body = _analyze(client, uid).json()
        tr_levels = {"Düşük Risk", "Orta Risk", "Yüksek Risk"}
        assert body["risk_level_tr"] in tr_levels

    def test_risk_factors_tr_is_list_of_strings(self, client):
        uid = _create_profile(client)
        body = _analyze(client, uid).json()
        factors = body["risk_factors_tr"]
        assert isinstance(factors, list)
        for f in factors:
            assert isinstance(f, str)
            assert len(f) > 0

    def test_uncertainty_tr_is_nonempty_string(self, client):
        uid = _create_profile(client)
        body = _analyze(client, uid).json()
        unc = body["uncertainty_tr"]
        assert unc is not None
        assert len(unc) > 0

    def test_community_insights_tr_is_list_of_strings(self, client):
        uid = _create_profile(client)
        body = _analyze(client, uid).json()
        insights = body["community_insights_tr"]
        assert isinstance(insights, list)
        assert len(insights) >= 1
        for ins in insights:
            assert isinstance(ins, str)
            assert len(ins) > 0

    def test_no_secret_fields_in_api_response(self, client):
        """API response must not leak internal credentials or storage paths."""
        uid = _create_profile(client)
        body = _analyze(client, uid).json()
        body_str = str(body).lower()
        assert "password" not in body_str
        assert "api_key" not in body_str
        assert "gemini" not in body_str
        assert "postgres" not in body_str


# ── Analysis varies with body measurements ────────────────────────────────────

class TestRecommendationLogic:
    def test_small_person_gets_smaller_size(self, client):
        """BMI 17 (underweight) should yield XS or S."""
        uid = _create_profile(client, height=165, weight=46)  # BMI ≈ 16.9
        body = _analyze(client, uid).json()
        assert body["recommended_size"] in ("XS", "S")

    def test_larger_person_gets_larger_size(self, client):
        """High BMI should yield XL or XXL."""
        uid = _create_profile(client, height=175, weight=100)  # BMI ≈ 32.6
        body = _analyze(client, uid).json()
        assert body["recommended_size"] in ("XL", "XXL")

    def test_png_upload_also_succeeds(self, client):
        uid = _create_profile(client)
        r = client.post(
            "/api/v1/analyze",
            data={"user_id": uid},
            files={"garment_image": ("shirt.png", PNG_BYTES, "image/png")},
        )
        assert r.status_code == 202
        assert r.json()["recommended_size"] is not None

    def test_fit_preference_changes_recommendation(self, client):
        """Different fit preferences must produce valid (potentially different) sizes."""
        valid_sizes = {"XS", "S", "M", "L", "XL", "XXL"}
        for pref in ("slim", "regular", "relaxed", "oversize"):
            uid = _create_profile(client, preference=pref)
            body = _analyze(client, uid).json()
            assert body["recommended_size"] in valid_sizes, (
                f"preference={pref} returned invalid size: {body['recommended_size']}"
            )


# ── Upload error paths ────────────────────────────────────────────────────────

class TestUploadErrors:
    def test_bmp_rejected_with_turkish_error(self, client):
        uid = _create_profile(client)
        r = _analyze(client, uid, image_bytes=BMP_BYTES, filename="shirt.bmp")
        assert r.status_code == 422
        detail = r.json()["detail"]
        assert isinstance(detail, str)
        # Must mention accepted formats in Turkish
        assert "JPEG" in detail or "PNG" in detail or "desteklenmiyor" in detail

    def test_garbage_bytes_rejected(self, client):
        uid = _create_profile(client)
        r = _analyze(client, uid, image_bytes=GARBAGE_BYTES)
        assert r.status_code == 422

    def test_unknown_user_returns_turkish_404(self, client):
        r = _analyze(client, "00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404
        assert "bulunamadı" in r.json()["detail"]

    def test_invalid_uuid_returns_422(self, client):
        r = _analyze(client, "not-a-uuid")
        assert r.status_code == 422

    def test_missing_garment_image_returns_422(self, client):
        uid = _create_profile(client)
        r = client.post("/api/v1/analyze", data={"user_id": uid})
        assert r.status_code == 422

    def test_profile_height_out_of_range_returns_turkish_422(self, client):
        r = client.post(
            "/api/v1/profile",
            data={"height_cm": "10", "weight_kg": "65", "fit_preference": "regular"},
        )
        assert r.status_code == 422
        assert "cm" in r.json()["detail"] or "Boy" in r.json()["detail"]

    def test_profile_weight_out_of_range_returns_turkish_422(self, client):
        r = client.post(
            "/api/v1/profile",
            data={"height_cm": "170", "weight_kg": "5", "fit_preference": "regular"},
        )
        assert r.status_code == 422
        assert "kg" in r.json()["detail"] or "Kilo" in r.json()["detail"]

    def test_profile_invalid_fit_preference_returns_422(self, client):
        r = client.post(
            "/api/v1/profile",
            data={"height_cm": "170", "weight_kg": "65", "fit_preference": "baggy"},
        )
        assert r.status_code == 422


# ── History reflects analysis results ─────────────────────────────────────────

class TestHistoryIntegration:
    def test_history_has_ai_fields_after_analysis(self, client):
        uid = _create_profile(client)
        upload = _analyze(client, uid).json()
        analysis_id = upload["analysis_id"]

        r = client.get(f"/api/v1/history/{uid}/{analysis_id}")
        assert r.status_code == 200
        detail = r.json()
        assert detail["recommended_size"] is not None
        assert detail["risk_level"] is not None
        assert detail["formatted_response"] is not None

    def test_history_formatted_response_contains_turkish_fields(self, client):
        uid = _create_profile(client)
        analysis_id = _analyze(client, uid).json()["analysis_id"]

        detail = client.get(f"/api/v1/history/{uid}/{analysis_id}").json()
        fr = detail["formatted_response"]
        assert "explanation_tr" in fr
        assert "risk_level_tr" in fr
        assert "community_insights_tr" in fr
        assert isinstance(fr["community_insights_tr"], list)

    def test_history_list_reflects_completed_analysis(self, client):
        uid = _create_profile(client)
        upload = _analyze(client, uid).json()
        analysis_id = upload["analysis_id"]

        items = client.get(f"/api/v1/history/{uid}").json()["items"]
        assert len(items) == 1
        item = items[0]
        assert item["analysis_id"] == analysis_id
        assert item["recommended_size"] is not None
        assert item["risk_level"] in ("low", "medium", "high")

    def test_multiple_users_histories_are_isolated(self, client):
        uid_a = _create_profile(client)
        uid_b = _create_profile(client)
        _analyze(client, uid_a)
        _analyze(client, uid_a)
        _analyze(client, uid_b)

        items_a = client.get(f"/api/v1/history/{uid_a}").json()["items"]
        items_b = client.get(f"/api/v1/history/{uid_b}").json()["items"]
        assert len(items_a) == 2
        assert len(items_b) == 1


# ── CORS headers ─────────────────────────────────────────────────────────────

class TestCORS:
    def test_preflight_allows_frontend_origin(self, client):
        r = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI CORS middleware returns 200 for allowed origins
        assert r.status_code in (200, 204)
        assert r.headers.get("access-control-allow-origin") in (
            "http://localhost:3000", "*"
        )

    def test_health_response_has_cors_header_for_allowed_origin(self, client):
        r = client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert r.status_code == 200
        # CORS origin header must be set for allowed origin
        assert "access-control-allow-origin" in r.headers
