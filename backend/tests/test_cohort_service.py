"""Tests for app.services.cohort — pure-Python aggregation, no DB."""

from app.services import cohort as cohort_mod
from app.services.cohort import (
    aggregate_return_reasons,
    find_similar_reviewers,
)


# ---------------------------------------------------------------------------
# Fixture cohorts — injected via _replace_reviews_for_test so we don't depend
# on the on-disk JSONL state for assertion-based tests.
# ---------------------------------------------------------------------------

def _fixture_rows(category: str = "shirt", brand: str = "standart",
                  n: int = 20, returned_n: int = 8,
                  reason: str = "boy_uzunluk",
                  height_cm: int = 175, weight_kg: int = 72) -> list[dict]:
    rows: list[dict] = []
    for i in range(n):
        is_returned = i < returned_n
        rows.append({
            "id": f"r{i:03d}",
            "garment_id": f"g{i:03d}",
            "_category": category,
            "_brand_sizing_tendency": brand,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "purchased_size": "M",
            "fits_true": not is_returned,
            "sentiment": "negative" if is_returned else "positive",
            "themes": "",
            "review_tr": f"Yorum {i}",
            "returned": is_returned,
            "return_reason": reason if is_returned else None,
            "fabric_breathability": "medium",
            "season_fit": "all_season",
        })
    return rows


# ---------------------------------------------------------------------------
# Cohort search — stage A → stage B fallback
# ---------------------------------------------------------------------------

def test_stage_a_when_enough_reviewers_match_body_envelope():
    cohort_mod._replace_reviews_for_test(
        _fixture_rows(category="shirt", brand="standart", n=20, returned_n=4)
    )
    rows, scope = find_similar_reviewers(
        category="shirt", brand_sizing_tendency="standart",
        height_cm=175, weight_kg=72,
    )
    assert scope.stage == "A"
    assert scope.total == 20
    assert "aynı kategori" in scope.label_tr
    assert "±5 cm boy" in scope.label_tr
    assert len(rows) == 20


def test_stage_b_falls_back_when_body_envelope_too_strict():
    # Reviews are far from the requested body envelope → stage A < 5 → fallback.
    rows_in = _fixture_rows(
        category="shirt", brand="küçük kalıplı",
        n=10, returned_n=3, height_cm=200, weight_kg=120,
    )
    cohort_mod._replace_reviews_for_test(rows_in)
    rows, scope = find_similar_reviewers(
        category="shirt", brand_sizing_tendency="küçük kalıplı",
        height_cm=160, weight_kg=55,
    )
    assert scope.stage == "B"
    assert scope.total == 10
    assert "(aynı kategori)" in scope.label_tr


def test_none_stage_when_no_category_matches():
    cohort_mod._replace_reviews_for_test(
        _fixture_rows(category="shirt", n=10, returned_n=0)
    )
    rows, scope = find_similar_reviewers(
        category="jeans", brand_sizing_tendency="standart",
        height_cm=170, weight_kg=65,
    )
    assert scope.stage == "none"
    assert rows == []
    assert "Yeterli benzer kullanıcı verisi yok" in scope.label_tr


# ---------------------------------------------------------------------------
# Aggregation + confidence bands
# ---------------------------------------------------------------------------

def test_high_confidence_band_n_ge_15():
    rows = _fixture_rows(n=20, returned_n=10, reason="boy_uzunluk")
    stats = aggregate_return_reasons(rows)
    assert stats.confidence_band == "high"
    assert stats.total == 20
    assert stats.returned_count == 10
    assert stats.returned_pct == 50
    assert stats.top_reasons[0].reason == "boy_uzunluk"
    assert stats.top_reasons[0].pct == 100             # 10/10 returned cited this
    assert stats.top_reasons[0].raw_count == 10


def test_medium_confidence_band_n_5_to_14():
    rows = _fixture_rows(n=10, returned_n=4, reason="omuz")
    stats = aggregate_return_reasons(rows)
    assert stats.confidence_band == "medium"
    assert stats.returned_pct == 40
    assert stats.top_reasons[0].reason_tr == "Omuz darlığı"


def test_low_band_suppresses_headline_pct_AND_reasons():
    # Only 3 reviewers → confidence band low → percentages must be suppressed.
    rows = _fixture_rows(n=3, returned_n=3, reason="kucuk_geldi")
    stats = aggregate_return_reasons(rows)
    assert stats.confidence_band == "low"
    assert stats.returned_pct is None              # honesty rail
    assert stats.top_reasons == []                 # no bars to publish


def test_no_returned_reviews_yields_zero_returned_pct():
    rows = _fixture_rows(n=15, returned_n=0)
    stats = aggregate_return_reasons(rows)
    assert stats.confidence_band == "high"
    assert stats.returned_count == 0
    assert stats.returned_pct == 0
    assert stats.top_reasons == []


def test_empty_cohort_returns_low_band():
    stats = aggregate_return_reasons([])
    assert stats.total == 0
    assert stats.confidence_band == "low"
    assert stats.returned_pct is None


def test_top_reasons_are_sorted_desc():
    rows = _fixture_rows(n=15, returned_n=9, reason="boy_uzunluk")
    # Mutate 3 of the returned rows to a different reason
    other_count = 0
    for r in rows:
        if r["returned"] and other_count < 3:
            r["return_reason"] = "kol"
            other_count += 1
    stats = aggregate_return_reasons(rows)
    # boy_uzunluk should appear first (6) then kol (3)
    assert stats.top_reasons[0].reason == "boy_uzunluk"
    assert stats.top_reasons[0].raw_count == 6
    assert stats.top_reasons[1].reason == "kol"
    assert stats.top_reasons[1].raw_count == 3


def test_sample_quotes_come_only_from_returned_reviewers():
    rows = _fixture_rows(n=10, returned_n=3, reason="omuz")
    stats = aggregate_return_reasons(rows)
    # All 3 quotes belong to indices 0, 1, 2 which are the returned ones.
    assert len(stats.sample_quotes_tr) == 3
    assert all("Yorum" in q for q in stats.sample_quotes_tr)
