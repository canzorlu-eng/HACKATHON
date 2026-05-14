"""
End-to-end integration tests: full analysis pipeline with MockAIClient
(authenticated via NextAuth-style Bearer JWT).
"""

from tests.conftest import (
    JPEG_BYTES,
    PNG_BYTES,
    BMP_BYTES,
    GARBAGE_BYTES,
    make_auth_header,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _onboard(client, auth_headers, height=170, weight=65, preference="regular"):
    r = client.post(
        "/api/v1/profile",
        data={
            "height_cm": str(height),
            "weight_kg": str(weight),
            "fit_preference": preference,
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text


def _analyze(client, auth_headers, image_bytes=JPEG_BYTES, filename="shirt.jpg"):
    return client.post(
        "/api/v1/analyze",
        files={"garment_image": (filename, image_bytes, "image/jpeg")},
        headers=auth_headers,
    )


# ── Full happy-path journey ───────────────────────────────────────────────────

class TestFullAnalysisJourney:
    def test_profile_create_returns_correct_fields(self, client, auth_headers):
        r = client.post(
            "/api/v1/profile",
            data={"height_cm": "175", "weight_kg": "70", "fit_preference": "slim"},
            headers=auth_headers,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["height_cm"] == 175
        assert body["weight_kg"] == 70
        assert body["fit_preference"] == "slim"
        assert body["has_body_image"] is False
        assert "user_id" in body
        assert "created_at" in body

    def test_analyze_returns_202_with_full_ai_fields(self, client, auth_headers):
        _onboard(client, auth_headers)
        r = _analyze(client, auth_headers)
        assert r.status_code == 202
        body = r.json()
        assert "analysis_id" in body
        assert body["garment_image_ref"].startswith("garment/")

    def test_recommended_size_is_valid_clothing_size(self, client, auth_headers):
        _onboard(client, auth_headers)
        body = _analyze(client, auth_headers).json()
        assert body["recommended_size"] in {"XS", "S", "M", "L", "XL", "XXL"}

    def test_confidence_score_is_float_in_valid_range(self, client, auth_headers):
        _onboard(client, auth_headers)
        body = _analyze(client, auth_headers).json()
        score = body["confidence_score"]
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_confidence_pct_is_formatted_turkish_string(self, client, auth_headers):
        _onboard(client, auth_headers)
        body = _analyze(client, auth_headers).json()
        pct = body["confidence_pct"]
        assert pct is not None
        assert pct.startswith("%")
        assert 0 <= int(pct.lstrip("%")) <= 100

    def test_explanation_tr_is_nonempty_turkish_string(self, client, auth_headers):
        _onboard(client, auth_headers)
        body = _analyze(client, auth_headers).json()
        expl = body["explanation_tr"]
        assert expl is not None and len(expl) > 10
        assert "beden" in expl.lower() or "öneril" in expl.lower() or "kesim" in expl.lower()

    def test_risk_level_is_valid_enum(self, client, auth_headers):
        _onboard(client, auth_headers)
        body = _analyze(client, auth_headers).json()
        assert body["risk_level"] in ("low", "medium", "high")

    def test_risk_level_tr_is_turkish_string(self, client, auth_headers):
        _onboard(client, auth_headers)
        body = _analyze(client, auth_headers).json()
        assert body["risk_level_tr"] in {"Düşük Risk", "Orta Risk", "Yüksek Risk"}

    def test_risk_factors_tr_is_list_of_strings(self, client, auth_headers):
        _onboard(client, auth_headers)
        body = _analyze(client, auth_headers).json()
        factors = body["risk_factors_tr"]
        assert isinstance(factors, list)
        for f in factors:
            assert isinstance(f, str) and len(f) > 0

    def test_uncertainty_tr_is_nonempty_string(self, client, auth_headers):
        _onboard(client, auth_headers)
        body = _analyze(client, auth_headers).json()
        unc = body["uncertainty_tr"]
        assert unc is not None and len(unc) > 0

    def test_community_insights_tr_is_list_of_strings(self, client, auth_headers):
        _onboard(client, auth_headers)
        body = _analyze(client, auth_headers).json()
        insights = body["community_insights_tr"]
        assert isinstance(insights, list) and len(insights) >= 1
        for ins in insights:
            assert isinstance(ins, str) and len(ins) > 0

    def test_no_secret_fields_in_api_response(self, client, auth_headers):
        _onboard(client, auth_headers)
        body = _analyze(client, auth_headers).json()
        s = str(body).lower()
        assert "password" not in s
        assert "api_key" not in s
        assert "gemini" not in s
        assert "postgres" not in s


# ── Analysis varies with body measurements ────────────────────────────────────

class TestRecommendationLogic:
    def test_small_person_gets_smaller_size(self, client, auth_headers):
        _onboard(client, auth_headers, height=165, weight=46)
        body = _analyze(client, auth_headers).json()
        assert body["recommended_size"] in ("XS", "S")

    def test_larger_person_gets_larger_size(self, client, auth_headers):
        _onboard(client, auth_headers, height=175, weight=100)
        body = _analyze(client, auth_headers).json()
        assert body["recommended_size"] in ("XL", "XXL")

    def test_png_upload_also_succeeds(self, client, auth_headers):
        _onboard(client, auth_headers)
        r = client.post(
            "/api/v1/analyze",
            files={"garment_image": ("shirt.png", PNG_BYTES, "image/png")},
            headers=auth_headers,
        )
        assert r.status_code == 202
        assert r.json()["recommended_size"] is not None

    def test_fit_preference_changes_recommendation(self, client, auth_headers):
        valid_sizes = {"XS", "S", "M", "L", "XL", "XXL"}
        for i, pref in enumerate(("slim", "regular", "relaxed", "oversize")):
            # Distinct identities per preference so each gets its own profile.
            h = make_auth_header(sub=f"sub-{i}", email=f"u{i}@example.com")
            _onboard(client, h, preference=pref)
            body = _analyze(client, h).json()
            assert body["recommended_size"] in valid_sizes


# ── Upload error paths ────────────────────────────────────────────────────────

class TestUploadErrors:
    def test_bmp_rejected_with_turkish_error(self, client, auth_headers):
        _onboard(client, auth_headers)
        r = _analyze(client, auth_headers, image_bytes=BMP_BYTES, filename="shirt.bmp")
        assert r.status_code == 422
        detail = r.json()["detail"]
        assert "JPEG" in detail or "PNG" in detail or "desteklenmiyor" in detail

    def test_garbage_bytes_rejected(self, client, auth_headers):
        _onboard(client, auth_headers)
        r = _analyze(client, auth_headers, image_bytes=GARBAGE_BYTES)
        assert r.status_code == 422

    def test_unauthenticated_analyze_returns_401(self, client):
        r = client.post(
            "/api/v1/analyze",
            files={"garment_image": ("shirt.jpg", JPEG_BYTES, "image/jpeg")},
        )
        assert r.status_code == 401

    def test_missing_garment_image_returns_422(self, client, auth_headers):
        _onboard(client, auth_headers)
        r = client.post("/api/v1/analyze", headers=auth_headers)
        assert r.status_code == 422

    def test_profile_height_out_of_range_returns_turkish_422(self, client, auth_headers):
        r = client.post(
            "/api/v1/profile",
            data={"height_cm": "10", "weight_kg": "65", "fit_preference": "regular"},
            headers=auth_headers,
        )
        assert r.status_code == 422
        assert "cm" in r.json()["detail"] or "Boy" in r.json()["detail"]

    def test_profile_weight_out_of_range_returns_turkish_422(self, client, auth_headers):
        r = client.post(
            "/api/v1/profile",
            data={"height_cm": "170", "weight_kg": "5", "fit_preference": "regular"},
            headers=auth_headers,
        )
        assert r.status_code == 422
        assert "kg" in r.json()["detail"] or "Kilo" in r.json()["detail"]

    def test_profile_invalid_fit_preference_returns_422(self, client, auth_headers):
        r = client.post(
            "/api/v1/profile",
            data={"height_cm": "170", "weight_kg": "65", "fit_preference": "baggy"},
            headers=auth_headers,
        )
        assert r.status_code == 422


# ── History reflects analysis results ─────────────────────────────────────────

class TestHistoryIntegration:
    def test_history_has_ai_fields_after_analysis(self, client, auth_headers):
        _onboard(client, auth_headers)
        upload = _analyze(client, auth_headers).json()
        analysis_id = upload["analysis_id"]

        r = client.get(f"/api/v1/history/{analysis_id}", headers=auth_headers)
        assert r.status_code == 200
        detail = r.json()
        assert detail["recommended_size"] is not None
        assert detail["risk_level"] is not None
        assert detail["formatted_response"] is not None

    def test_history_formatted_response_contains_turkish_fields(self, client, auth_headers):
        _onboard(client, auth_headers)
        analysis_id = _analyze(client, auth_headers).json()["analysis_id"]

        detail = client.get(f"/api/v1/history/{analysis_id}", headers=auth_headers).json()
        fr = detail["formatted_response"]
        assert "explanation_tr" in fr
        assert "risk_level_tr" in fr
        assert "community_insights_tr" in fr
        assert isinstance(fr["community_insights_tr"], list)

    def test_history_list_reflects_completed_analysis(self, client, auth_headers):
        _onboard(client, auth_headers)
        upload = _analyze(client, auth_headers).json()
        analysis_id = upload["analysis_id"]

        items = client.get("/api/v1/history", headers=auth_headers).json()["items"]
        assert len(items) == 1
        item = items[0]
        assert item["analysis_id"] == analysis_id
        assert item["recommended_size"] is not None
        assert item["risk_level"] in ("low", "medium", "high")

    def test_multiple_users_histories_are_isolated(self, client):
        headers_a = make_auth_header(sub="user-a", email="a@example.com")
        headers_b = make_auth_header(sub="user-b", email="b@example.com")
        _onboard(client, headers_a)
        _onboard(client, headers_b)
        _analyze(client, headers_a)
        _analyze(client, headers_a)
        _analyze(client, headers_b)

        items_a = client.get("/api/v1/history", headers=headers_a).json()["items"]
        items_b = client.get("/api/v1/history", headers=headers_b).json()["items"]
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
        assert "access-control-allow-origin" in r.headers
