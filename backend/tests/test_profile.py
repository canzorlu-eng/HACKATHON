"""Tests for UC-01: profile creation and retrieval (authenticated)."""

from tests.conftest import JPEG_BYTES, PNG_BYTES


def _profile_form(**overrides):
    base = {"height_cm": "175", "weight_kg": "70", "fit_preference": "regular"}
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------

def test_create_profile_no_image(client, auth_headers):
    r = client.post("/api/v1/profile", data=_profile_form(), headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["has_body_image"] is False
    assert body["height_cm"] == 175
    assert body["fit_preference"] == "regular"
    assert "user_id" in body


def test_create_profile_with_jpeg(client, auth_headers):
    r = client.post(
        "/api/v1/profile",
        data=_profile_form(),
        files={"body_image": ("photo.jpg", JPEG_BYTES, "image/jpeg")},
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert r.json()["has_body_image"] is True


def test_create_profile_with_png(client, auth_headers):
    r = client.post(
        "/api/v1/profile",
        data=_profile_form(),
        files={"body_image": ("photo.png", PNG_BYTES, "image/png")},
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert r.json()["has_body_image"] is True


def test_get_profile_me_returns_created(client, auth_headers):
    client.post("/api/v1/profile", data=_profile_form(), headers=auth_headers)
    get_r = client.get("/api/v1/profile/me", headers=auth_headers)
    assert get_r.status_code == 200
    assert get_r.json()["height_cm"] == 175


def test_all_fit_preferences_accepted(client, auth_headers):
    for pref in ("slim", "regular", "relaxed", "oversize"):
        r = client.post(
            "/api/v1/profile",
            data=_profile_form(fit_preference=pref),
            headers=auth_headers,
        )
        assert r.status_code == 201, f"Expected 201 for fit_preference={pref}"


# ---------------------------------------------------------------------------
# Validation failures
# ---------------------------------------------------------------------------

def test_missing_height_rejected(client, auth_headers):
    data = {"weight_kg": "70", "fit_preference": "regular"}
    r = client.post("/api/v1/profile", data=data, headers=auth_headers)
    assert r.status_code == 422


def test_missing_weight_rejected(client, auth_headers):
    data = {"height_cm": "175", "fit_preference": "regular"}
    r = client.post("/api/v1/profile", data=data, headers=auth_headers)
    assert r.status_code == 422


def test_missing_fit_preference_rejected(client, auth_headers):
    data = {"height_cm": "175", "weight_kg": "70"}
    r = client.post("/api/v1/profile", data=data, headers=auth_headers)
    assert r.status_code == 422


def test_height_too_low_rejected(client, auth_headers):
    r = client.post(
        "/api/v1/profile",
        data=_profile_form(height_cm="30"),
        headers=auth_headers,
    )
    assert r.status_code == 422
    assert "Boy" in r.json()["detail"]


def test_height_too_high_rejected(client, auth_headers):
    r = client.post(
        "/api/v1/profile",
        data=_profile_form(height_cm="350"),
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_weight_too_low_rejected(client, auth_headers):
    r = client.post(
        "/api/v1/profile",
        data=_profile_form(weight_kg="5"),
        headers=auth_headers,
    )
    assert r.status_code == 422
    assert "Kilo" in r.json()["detail"]


def test_invalid_fit_preference_rejected(client, auth_headers):
    r = client.post(
        "/api/v1/profile",
        data=_profile_form(fit_preference="baggy"),
        headers=auth_headers,
    )
    assert r.status_code == 422
    assert "uyum tercihi" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Auth gating
# ---------------------------------------------------------------------------

def test_profile_me_without_token_rejected(client):
    r = client.get("/api/v1/profile/me")
    assert r.status_code == 401


def test_profile_me_returns_404_when_user_has_no_profile(client, auth_headers):
    # Token is valid → user row gets created on first call, but with no
    # measurements yet, so /profile/me should signal onboarding is needed.
    r = client.get("/api/v1/profile/me", headers=auth_headers)
    assert r.status_code == 404
    assert "Profil" in r.json()["detail"]
