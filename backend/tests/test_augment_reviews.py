"""Tests for backend/scripts/augment_reviews.py — deterministic enrichment."""

import pytest

from scripts.augment_reviews import (
    _classify_return_reason,
    _is_returned,
    enrich_row,
)


# ---------------------------------------------------------------------------
# Returned proxy
# ---------------------------------------------------------------------------

def test_returned_requires_negative_sentiment_AND_misfit():
    assert _is_returned(False, "negative") is True
    assert _is_returned(False, "neutral")  is False   # neutral != returned
    assert _is_returned(True,  "negative") is False   # fit OK → kept
    assert _is_returned(True,  "positive") is False


# ---------------------------------------------------------------------------
# Return reason precedence — chosen specifically so order matters
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("themes,review_tr,expected", [
    ("küçük kalıplı,dar omuz",     "omuzlarım sığmadı",          "omuz"),         # omuz beats kucuk_geldi
    ("dar gövde",                  "gövde bölümü dar geldi",     "kalca_bel"),    # gövde → kalca_bel
    ("dar kol,slim kesim",         "kollar çok dar",              "kol"),          # kol beats kucuk_geldi
    ("küçük kalıplı",              "etek boyu kısa kaldı",        "boy_uzunluk"),  # boy beats kucuk_geldi
    ("küçük kalıplı",              "M beden slim gibi oturdu",    "kucuk_geldi"),  # generic small
    ("büyük kalıplı",              "fazla bol geldi",             "buyuk_geldi"),  # generic big
    ("ince kumaş",                 "kumaş çok ucuz, şeffaf",      "kumas"),        # fabric
    ("renk farklı",                "renk farklı geldi, fotoğraftaki gibi değil", "renk_farkli"),
    ("",                           "iade ettim ama tam neden hatırlamıyorum",    "genel_uyumsuzluk"),
])
def test_classify_return_reason_precedence(themes, review_tr, expected):
    assert _classify_return_reason(themes, review_tr) == expected


# ---------------------------------------------------------------------------
# enrich_row end-to-end
# ---------------------------------------------------------------------------

def test_enrich_row_marks_negative_misfit_as_returned():
    garments = {
        "g001": {"fabric": "Pamuklu poplin, orta ağırlık", "category": "shirt"},
    }
    row = {
        "id": "x", "garment_id": "g001",
        "height_cm": 178, "weight_kg": 78,
        "purchased_size": "L", "fits_true": False,
        "themes": "küçük kalıplı,dar omuz",
        "sentiment": "negative",
        "review_tr": "Omuzlarım sığmadı.",
    }
    out = enrich_row(row, garments)
    assert out["returned"] is True
    assert out["return_reason"] == "omuz"
    assert out["fabric_breathability"] == "medium"
    assert out["season_fit"] == "all_season"


def test_enrich_row_does_not_assign_reason_when_not_returned():
    garments = {"g001": {"fabric": "Keten", "category": "shirt"}}
    row = {
        "id": "x", "garment_id": "g001",
        "fits_true": True, "sentiment": "positive",
        "themes": "iyi dikiş", "review_tr": "Çok beğendim.",
    }
    out = enrich_row(row, garments)
    assert out["returned"] is False
    assert out["return_reason"] is None
    assert out["fabric_breathability"] == "high"   # Keten → high


def test_enrich_row_does_not_mutate_input():
    garments = {"g001": {"fabric": "polar", "category": "jacket"}}
    row = {
        "id": "x", "garment_id": "g001",
        "fits_true": False, "sentiment": "negative",
        "themes": "kumaş kalın", "review_tr": "Aşırı sıcak tuttu.",
    }
    snapshot = dict(row)
    enrich_row(row, garments)
    assert row == snapshot                          # caller's dict untouched


def test_enrich_row_jacket_is_winter_regardless_of_fabric_keys():
    garments = {"g001": {"fabric": "Naylon dış yüz, tüy dolgu", "category": "jacket"}}
    row = {"id": "x", "garment_id": "g001", "fits_true": True, "sentiment": "positive",
           "themes": "", "review_tr": ""}
    assert enrich_row(row, garments)["season_fit"] == "winter"
