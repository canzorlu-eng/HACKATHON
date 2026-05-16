"""Integration tests for GET /api/v1/analyses/{id}/cohort."""

from tests.conftest import JPEG_BYTES


def _onboard(client, auth_headers, height=170, weight=65):
    r = client.post(
        "/api/v1/profile",
        data={"height_cm": str(height), "weight_kg": str(weight), "fit_preference": "regular"},
        headers=auth_headers,
    )
    assert r.status_code == 201


def _upload(client, auth_headers):
    r = client.post(
        "/api/v1/analyze",
        files={"garment_image": ("shirt.jpg", JPEG_BYTES, "image/jpeg")},
        headers=auth_headers,
    )
    assert r.status_code == 202
    return r.json()["analysis_id"]


# ---------------------------------------------------------------------------
# Auth + ownership
# ---------------------------------------------------------------------------

def test_cohort_unauthenticated_returns_401(client):
    r = client.get("/api/v1/analyses/00000000-0000-0000-0000-000000000000/cohort")
    assert r.status_code == 401


def test_cohort_unknown_id_returns_404(client, auth_headers):
    _onboard(client, auth_headers)
    r = client.get(
        "/api/v1/analyses/00000000-0000-0000-0000-000000000000/cohort",
        headers=auth_headers,
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_cohort_returns_scope_and_band(client, auth_headers):
    _onboard(client, auth_headers)
    aid = _upload(client, auth_headers)
    r = client.get(f"/api/v1/analyses/{aid}/cohort", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert "scope_tr" in body
    assert body["confidence_band"] in ("low", "medium", "high")
    assert isinstance(body["top_reasons"], list)
    assert isinstance(body["sample_quotes_tr"], list)


def test_cohort_low_band_suppresses_pct_and_reasons(client, auth_headers):
    # Extreme body metrics → tiny cohort → low band → no pct, no reasons.
    _onboard(client, auth_headers, height=199, weight=140)
    aid = _upload(client, auth_headers)
    r = client.get(f"/api/v1/analyses/{aid}/cohort", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    if body["confidence_band"] == "low":
        assert body["returned_pct"] is None
        assert body["top_reasons"] == []


def test_cohort_returns_empty_when_analysis_is_garment_invalid(
    client, auth_headers, db_session,
):
    from uuid import uuid4
    from app.models.analysis import Analysis
    from app.repositories.users import UserRepository

    _onboard(client, auth_headers)
    user = UserRepository(db_session).get_by_google_sub("test-google-sub-1")
    assert user is not None

    a = Analysis(
        id=uuid4(),
        user_id=user.id,
        garment_image_ref="invalid.jpg",
        recommended_size=None,           # ← garment-invalid signal
        formatted_response={
            "recommended_size": None,
            "explanation_tr": "Yüklenen görselde tanınabilir bir kıyafet bulunamadı.",
        },
    )
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)

    r = client.get(f"/api/v1/analyses/{a.id}/cohort", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["confidence_band"] == "low"
    assert body["total"] == 0
    assert body["returned_pct"] is None
    assert body["top_reasons"] == []
