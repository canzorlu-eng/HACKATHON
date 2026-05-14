"""Tests for UC-02: garment image upload validation (authenticated)."""

from tests.conftest import BMP_BYTES, GARBAGE_BYTES, JPEG_BYTES, PNG_BYTES, TRUNCATED_BYTES


def _onboard(client, auth_headers):
    """Set the auth user's measurements so /analyze doesn't 409."""
    r = client.post(
        "/api/v1/profile",
        data={"height_cm": "170", "weight_kg": "65", "fit_preference": "regular"},
        headers=auth_headers,
    )
    assert r.status_code == 201


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------

def test_upload_jpeg_garment_accepted(client, auth_headers):
    _onboard(client, auth_headers)
    r = client.post(
        "/api/v1/analyze",
        files={"garment_image": ("shirt.jpg", JPEG_BYTES, "image/jpeg")},
        headers=auth_headers,
    )
    assert r.status_code == 202
    body = r.json()
    assert "analysis_id" in body
    assert body["garment_image_ref"].startswith("garment/")
    assert "Görsel doğrulandı" in body["message"]


def test_upload_png_garment_accepted(client, auth_headers):
    _onboard(client, auth_headers)
    r = client.post(
        "/api/v1/analyze",
        files={"garment_image": ("shirt.png", PNG_BYTES, "image/png")},
        headers=auth_headers,
    )
    assert r.status_code == 202


# ---------------------------------------------------------------------------
# Format rejection — magic-byte checks
# ---------------------------------------------------------------------------

def test_bmp_garment_rejected(client, auth_headers):
    _onboard(client, auth_headers)
    r = client.post(
        "/api/v1/analyze",
        files={"garment_image": ("shirt.bmp", BMP_BYTES, "image/bmp")},
        headers=auth_headers,
    )
    assert r.status_code == 422
    assert "JPEG" in r.json()["detail"] or "PNG" in r.json()["detail"]


def test_garbage_bytes_rejected(client, auth_headers):
    _onboard(client, auth_headers)
    r = client.post(
        "/api/v1/analyze",
        files={"garment_image": ("shirt.jpg", GARBAGE_BYTES, "image/jpeg")},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_truncated_file_rejected(client, auth_headers):
    _onboard(client, auth_headers)
    r = client.post(
        "/api/v1/analyze",
        files={"garment_image": ("shirt.jpg", TRUNCATED_BYTES, "image/jpeg")},
        headers=auth_headers,
    )
    assert r.status_code == 422
    assert "küçük" in r.json()["detail"]


def test_wrong_extension_but_valid_jpeg_magic_accepted(client, auth_headers):
    """The validator checks magic bytes, not file extension."""
    _onboard(client, auth_headers)
    r = client.post(
        "/api/v1/analyze",
        files={"garment_image": ("shirt.png", JPEG_BYTES, "image/jpeg")},
        headers=auth_headers,
    )
    assert r.status_code == 202


# ---------------------------------------------------------------------------
# Auth / profile checks
# ---------------------------------------------------------------------------

def test_unauthenticated_analyze_returns_401(client):
    r = client.post(
        "/api/v1/analyze",
        files={"garment_image": ("shirt.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert r.status_code == 401


def test_authenticated_but_no_profile_returns_409(client, auth_headers):
    # Valid token, but the user has not finished onboarding yet.
    r = client.post(
        "/api/v1/analyze",
        files={"garment_image": ("shirt.jpg", JPEG_BYTES, "image/jpeg")},
        headers=auth_headers,
    )
    assert r.status_code == 409
    assert "Profil" in r.json()["detail"]


def test_missing_garment_image_returns_422(client, auth_headers):
    _onboard(client, auth_headers)
    r = client.post("/api/v1/analyze", headers=auth_headers)
    assert r.status_code == 422
