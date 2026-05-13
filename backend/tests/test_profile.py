"""Tests for UC-01: profile creation and retrieval."""

import pytest
from tests.conftest import JPEG_BYTES, PNG_BYTES


def _profile_form(**overrides):
    base = {"height_cm": "175", "weight_kg": "70", "fit_preference": "regular"}
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------

def test_create_profile_no_image(client):
    r = client.post("/api/v1/profile", data=_profile_form())
    assert r.status_code == 201
    body = r.json()
    assert body["has_body_image"] is False
    assert body["height_cm"] == 175
    assert body["fit_preference"] == "regular"
    assert "user_id" in body


def test_create_profile_with_jpeg(client):
    r = client.post(
        "/api/v1/profile",
        data=_profile_form(),
        files={"body_image": ("photo.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert r.status_code == 201
    assert r.json()["has_body_image"] is True


def test_create_profile_with_png(client):
    r = client.post(
        "/api/v1/profile",
        data=_profile_form(),
        files={"body_image": ("photo.png", PNG_BYTES, "image/png")},
    )
    assert r.status_code == 201
    assert r.json()["has_body_image"] is True


def test_get_profile_returns_created(client):
    create_r = client.post("/api/v1/profile", data=_profile_form())
    uid = create_r.json()["user_id"]

    get_r = client.get(f"/api/v1/profile/{uid}")
    assert get_r.status_code == 200
    assert get_r.json()["user_id"] == uid


def test_all_fit_preferences_accepted(client):
    for pref in ("slim", "regular", "relaxed", "oversize"):
        r = client.post("/api/v1/profile", data=_profile_form(fit_preference=pref))
        assert r.status_code == 201, f"Expected 201 for fit_preference={pref}"


# ---------------------------------------------------------------------------
# Validation failures — missing / invalid fields
# ---------------------------------------------------------------------------

def test_missing_height_rejected(client):
    data = {"weight_kg": "70", "fit_preference": "regular"}
    r = client.post("/api/v1/profile", data=data)
    assert r.status_code == 422


def test_missing_weight_rejected(client):
    data = {"height_cm": "175", "fit_preference": "regular"}
    r = client.post("/api/v1/profile", data=data)
    assert r.status_code == 422


def test_missing_fit_preference_rejected(client):
    data = {"height_cm": "175", "weight_kg": "70"}
    r = client.post("/api/v1/profile", data=data)
    assert r.status_code == 422


def test_height_too_low_rejected(client):
    r = client.post("/api/v1/profile", data=_profile_form(height_cm="30"))
    assert r.status_code == 422
    assert "Boy" in r.json()["detail"]


def test_height_too_high_rejected(client):
    r = client.post("/api/v1/profile", data=_profile_form(height_cm="350"))
    assert r.status_code == 422


def test_weight_too_low_rejected(client):
    r = client.post("/api/v1/profile", data=_profile_form(weight_kg="5"))
    assert r.status_code == 422
    assert "Kilo" in r.json()["detail"]


def test_invalid_fit_preference_rejected(client):
    r = client.post("/api/v1/profile", data=_profile_form(fit_preference="baggy"))
    assert r.status_code == 422
    assert "uyum tercihi" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Profile retrieval errors
# ---------------------------------------------------------------------------

def test_get_unknown_profile_returns_404(client):
    r = client.get("/api/v1/profile/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
    assert "bulunamadı" in r.json()["detail"]
