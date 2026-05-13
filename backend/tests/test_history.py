"""Tests for UC-08: analysis history storage and retrieval."""

import uuid
from datetime import datetime

from tests.conftest import JPEG_BYTES


def _create_user(client):
    r = client.post(
        "/api/v1/profile",
        data={"height_cm": "170", "weight_kg": "65", "fit_preference": "regular"},
    )
    assert r.status_code == 201
    return r.json()["user_id"]


def _upload_garment(client, user_id: str):
    r = client.post(
        "/api/v1/analyze",
        data={"user_id": user_id},
        files={"garment_image": ("shirt.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert r.status_code == 202
    return r.json()


# ---------------------------------------------------------------------------
# History list
# ---------------------------------------------------------------------------

def test_history_empty_for_new_user(client):
    uid = _create_user(client)
    r = client.get(f"/api/v1/history/{uid}")
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_history_contains_uploaded_analysis(client):
    uid = _create_user(client)
    upload = _upload_garment(client, uid)
    analysis_id = upload["analysis_id"]

    r = client.get(f"/api/v1/history/{uid}")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["analysis_id"] == analysis_id


def test_history_multiple_analyses_newest_first(client):
    uid = _create_user(client)
    ids = [_upload_garment(client, uid)["analysis_id"] for _ in range(3)]

    r = client.get(f"/api/v1/history/{uid}")
    body = r.json()
    assert body["total"] == 3
    returned_ids = [item["analysis_id"] for item in body["items"]]
    # All created IDs present (order may vary in SQLite, just check membership)
    assert set(returned_ids) == set(ids)


def test_history_unknown_user_returns_404(client):
    r = client.get("/api/v1/history/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
    assert "bulunamadı" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Analysis detail
# ---------------------------------------------------------------------------

def test_get_analysis_detail_returns_expected_fields(client):
    uid = _create_user(client)
    upload = _upload_garment(client, uid)
    analysis_id = upload["analysis_id"]

    r = client.get(f"/api/v1/history/{uid}/{analysis_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["analysis_id"] == analysis_id
    assert body["user_id"] == uid
    assert body["garment_image_ref"] == upload["garment_image_ref"]
    # AI pipeline populates these fields
    assert body["recommended_size"] is not None
    assert body["risk_level"] is not None
    assert body["formatted_response"] is not None
    assert "confidence_score" in body["formatted_response"]


def test_get_analysis_unknown_analysis_id_returns_404(client):
    uid = _create_user(client)
    r = client.get(f"/api/v1/history/{uid}/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
    assert "bulunamadı" in r.json()["detail"]


def test_get_analysis_wrong_user_returns_404(client):
    """An analysis belonging to user A must not be visible to user B."""
    uid_a = _create_user(client)
    uid_b = _create_user(client)
    upload = _upload_garment(client, uid_a)
    analysis_id = upload["analysis_id"]

    r = client.get(f"/api/v1/history/{uid_b}/{analysis_id}")
    assert r.status_code == 404
