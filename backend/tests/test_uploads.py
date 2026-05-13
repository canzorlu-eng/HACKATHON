"""Tests for UC-02: garment image upload validation."""

import pytest
from tests.conftest import BMP_BYTES, GARBAGE_BYTES, JPEG_BYTES, PNG_BYTES, TRUNCATED_BYTES


def _create_user(client):
    r = client.post(
        "/api/v1/profile",
        data={"height_cm": "170", "weight_kg": "65", "fit_preference": "regular"},
    )
    assert r.status_code == 201
    return r.json()["user_id"]


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------

def test_upload_jpeg_garment_accepted(client):
    uid = _create_user(client)
    r = client.post(
        "/api/v1/analyze",
        data={"user_id": uid},
        files={"garment_image": ("shirt.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert r.status_code == 202
    body = r.json()
    assert "analysis_id" in body
    assert body["garment_image_ref"].startswith("garment/")
    # Turkish stub message present
    assert "Görsel doğrulandı" in body["message"]


def test_upload_png_garment_accepted(client):
    uid = _create_user(client)
    r = client.post(
        "/api/v1/analyze",
        data={"user_id": uid},
        files={"garment_image": ("shirt.png", PNG_BYTES, "image/png")},
    )
    assert r.status_code == 202


# ---------------------------------------------------------------------------
# Format rejection — magic-byte checks
# ---------------------------------------------------------------------------

def test_bmp_garment_rejected(client):
    uid = _create_user(client)
    r = client.post(
        "/api/v1/analyze",
        data={"user_id": uid},
        files={"garment_image": ("shirt.bmp", BMP_BYTES, "image/bmp")},
    )
    assert r.status_code == 422
    assert "JPEG" in r.json()["detail"] or "PNG" in r.json()["detail"]


def test_garbage_bytes_rejected(client):
    uid = _create_user(client)
    r = client.post(
        "/api/v1/analyze",
        data={"user_id": uid},
        files={"garment_image": ("shirt.jpg", GARBAGE_BYTES, "image/jpeg")},
    )
    assert r.status_code == 422


def test_truncated_file_rejected(client):
    uid = _create_user(client)
    r = client.post(
        "/api/v1/analyze",
        data={"user_id": uid},
        files={"garment_image": ("shirt.jpg", TRUNCATED_BYTES, "image/jpeg")},
    )
    assert r.status_code == 422
    assert "küçük" in r.json()["detail"]


def test_wrong_extension_but_valid_jpeg_magic_accepted(client):
    """The validator checks magic bytes, not file extension."""
    uid = _create_user(client)
    r = client.post(
        "/api/v1/analyze",
        data={"user_id": uid},
        # .png extension, but JPEG magic bytes — should still be accepted as JPEG
        files={"garment_image": ("shirt.png", JPEG_BYTES, "image/jpeg")},
    )
    assert r.status_code == 202


def test_oversized_file_rejected(client, monkeypatch):
    """Files exceeding MAX_UPLOAD_MB must be rejected with a Turkish error."""
    from app.config import get_settings
    # Temporarily set limit to 1 byte so any real image overflows
    monkeypatch.setattr(get_settings(), "max_upload_mb", 0, raising=False)
    # Clear cache and re-patch settings
    get_settings.cache_clear()
    monkeypatch.setenv("MAX_UPLOAD_MB", "0")
    get_settings.cache_clear()

    uid = _create_user(client)
    r = client.post(
        "/api/v1/analyze",
        data={"user_id": uid},
        files={"garment_image": ("shirt.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert r.status_code == 422
    assert "büyük" in r.json()["detail"]

    monkeypatch.setenv("MAX_UPLOAD_MB", "8")
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Auth / user checks
# ---------------------------------------------------------------------------

def test_unknown_user_returns_404(client):
    r = client.post(
        "/api/v1/analyze",
        data={"user_id": "00000000-0000-0000-0000-000000000000"},
        files={"garment_image": ("shirt.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert r.status_code == 404
    assert "bulunamadı" in r.json()["detail"]


def test_invalid_uuid_returns_422(client):
    r = client.post(
        "/api/v1/analyze",
        data={"user_id": "not-a-uuid"},
        files={"garment_image": ("shirt.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert r.status_code == 422


def test_missing_garment_image_returns_422(client):
    uid = _create_user(client)
    r = client.post("/api/v1/analyze", data={"user_id": uid})
    assert r.status_code == 422
