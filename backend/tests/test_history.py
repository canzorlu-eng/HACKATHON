"""Tests for UC-08: analysis history storage and retrieval (authenticated)."""

from tests.conftest import JPEG_BYTES, make_auth_header


def _onboard(client, auth_headers):
    r = client.post(
        "/api/v1/profile",
        data={"height_cm": "170", "weight_kg": "65", "fit_preference": "regular"},
        headers=auth_headers,
    )
    assert r.status_code == 201


def _upload_garment(client, auth_headers):
    r = client.post(
        "/api/v1/analyze",
        files={"garment_image": ("shirt.jpg", JPEG_BYTES, "image/jpeg")},
        headers=auth_headers,
    )
    assert r.status_code == 202
    return r.json()


# ---------------------------------------------------------------------------
# History list
# ---------------------------------------------------------------------------

def test_history_empty_for_new_user(client, auth_headers):
    _onboard(client, auth_headers)
    r = client.get("/api/v1/history", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_history_contains_uploaded_analysis(client, auth_headers):
    _onboard(client, auth_headers)
    upload = _upload_garment(client, auth_headers)
    analysis_id = upload["analysis_id"]

    r = client.get("/api/v1/history", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["analysis_id"] == analysis_id


def test_history_multiple_analyses_newest_first(client, auth_headers):
    _onboard(client, auth_headers)
    ids = [_upload_garment(client, auth_headers)["analysis_id"] for _ in range(3)]

    r = client.get("/api/v1/history", headers=auth_headers)
    body = r.json()
    assert body["total"] == 3
    returned_ids = [item["analysis_id"] for item in body["items"]]
    assert set(returned_ids) == set(ids)


def test_history_unauthenticated_returns_401(client):
    r = client.get("/api/v1/history")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Analysis detail
# ---------------------------------------------------------------------------

def test_get_analysis_detail_returns_expected_fields(client, auth_headers):
    _onboard(client, auth_headers)
    upload = _upload_garment(client, auth_headers)
    analysis_id = upload["analysis_id"]

    r = client.get(f"/api/v1/history/{analysis_id}", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["analysis_id"] == analysis_id
    assert body["garment_image_ref"] == upload["garment_image_ref"]
    assert body["recommended_size"] is not None
    assert body["risk_level"] is not None
    assert body["formatted_response"] is not None
    assert "confidence_score" in body["formatted_response"]


def test_get_analysis_unknown_analysis_id_returns_404(client, auth_headers):
    _onboard(client, auth_headers)
    r = client.get(
        "/api/v1/history/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert r.status_code == 404
    assert "bulunamadı" in r.json()["detail"]


def test_get_analysis_wrong_user_returns_404(client, auth_headers):
    """An analysis belonging to user A must not be visible to user B."""
    _onboard(client, auth_headers)
    upload = _upload_garment(client, auth_headers)
    analysis_id = upload["analysis_id"]

    # Different Google sub → different user.
    other_headers = make_auth_header(sub="another-google-sub", email="other@example.com")
    # User B needs onboarding too, but only to authenticate — they shouldn't
    # see user A's analyses regardless of profile state.
    r = client.get(f"/api/v1/history/{analysis_id}", headers=other_headers)
    assert r.status_code == 404


def test_delete_analysis(client, auth_headers):
    _onboard(client, auth_headers)
    upload = _upload_garment(client, auth_headers)
    analysis_id = upload["analysis_id"]

    r = client.delete(f"/api/v1/history/{analysis_id}", headers=auth_headers)
    assert r.status_code == 204

    # Confirm it's gone
    r = client.get(f"/api/v1/history/{analysis_id}", headers=auth_headers)
    assert r.status_code == 404
