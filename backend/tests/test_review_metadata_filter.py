"""Tests for the metadata where-clause + tiered fallback in review_service."""

from app.services.review_service import (
    ReviewIntelligenceService,
    _where_matches,
)


# ---------------------------------------------------------------------------
# _build_where  (pure)
# ---------------------------------------------------------------------------

def test_build_where_returns_none_when_all_filters_empty():
    assert ReviewIntelligenceService._build_where({}) is None
    assert ReviewIntelligenceService._build_where({"category": None, "fit_type": ""}) is None


def test_build_where_single_clause_is_flat():
    out = ReviewIntelligenceService._build_where({"category": "shirt"})
    assert out == {"category": {"$eq": "shirt"}}


def test_build_where_multiple_clauses_uses_and():
    out = ReviewIntelligenceService._build_where(
        {"category": "shirt", "fit_type": "slim-cut"}
    )
    assert out == {"$and": [
        {"category": {"$eq": "shirt"}},
        {"fit_type": {"$eq": "slim-cut"}},
    ]}


# ---------------------------------------------------------------------------
# _where_matches  (mirror of Chroma's $eq / $and for the demo collection)
# ---------------------------------------------------------------------------

def test_where_matches_none_always_true():
    assert _where_matches({"category": "shirt"}, None) is True


def test_where_matches_eq_pass_and_fail():
    assert _where_matches({"category": "shirt"}, {"category": {"$eq": "shirt"}}) is True
    assert _where_matches({"category": "shirt"}, {"category": {"$eq": "jeans"}}) is False


def test_where_matches_and_requires_all_subclauses():
    meta = {"category": "shirt", "fit_type": "slim-cut"}
    ok   = {"$and": [{"category": {"$eq": "shirt"}}, {"fit_type": {"$eq": "slim-cut"}}]}
    bad  = {"$and": [{"category": {"$eq": "shirt"}}, {"fit_type": {"$eq": "oversize"}}]}
    assert _where_matches(meta, ok) is True
    assert _where_matches(meta, bad) is False


# ---------------------------------------------------------------------------
# Tiered fallback via a stub collection
# ---------------------------------------------------------------------------

class _StubCollection:
    """Records every query and applies _where_matches like _DemoCollection."""
    def __init__(self, docs: list[dict]) -> None:
        self._docs = docs
        self.calls: list[dict | None] = []

    def count(self) -> int:
        return len(self._docs)

    def query(self, query_texts, n_results, include, where=None):  # noqa: ARG002
        self.calls.append(where)
        matched = [d for d in self._docs if _where_matches(d["meta"], where)]
        sample = matched[: min(n_results, len(matched))]
        return {
            "documents": [[d["text"] for d in sample]],
            "metadatas": [[d["meta"] for d in sample]],
            "distances": [[0.2] * len(sample)],
        }


def _doc(i: int, **meta) -> dict:
    base = {
        "garment_id": f"g{i}",
        "purchased_size": "M",
        "fits_true": "True",
        "themes": "iyi kesim",
        "sentiment": "positive",
    }
    base.update({k: str(v) for k, v in meta.items()})
    return {"text": f"yorum {i}", "meta": base}


def _build_service(docs: list[dict]) -> tuple[ReviewIntelligenceService, _StubCollection]:
    col = _StubCollection(docs)

    class _Client:
        def get_or_create_collection(self, **kw):  # noqa: ARG002
            return col

    svc = ReviewIntelligenceService(_Client(), collection_name="reviews_test")
    return svc, col


def test_strict_filter_hits_when_data_available():
    docs = [
        _doc(1, category="shirt", fit_type="regular",
             season_fit="all_season", fabric_breathability="medium"),
        _doc(2, category="shirt", fit_type="regular",
             season_fit="all_season", fabric_breathability="medium"),
        _doc(3, category="jeans", fit_type="slim-cut",
             season_fit="all_season", fabric_breathability="medium"),
    ]
    svc, col = _build_service(docs)
    result = svc.query(
        "shirt", "regular", "standart",
        season_fit="all_season", fabric_breathability="medium",
    )
    assert result.status == "ok"
    # Strict tier was the first try AND it returned results — no relaxation.
    assert len(col.calls) == 1
    # And the strict where joined all 4 keys.
    where = col.calls[0]
    assert where is not None
    assert "$and" in where


def test_tiered_relaxation_drops_filters_until_match():
    # Reviews exist for the category but none with the requested breathability,
    # season, OR fit_type. Service must walk down to category_only.
    docs = [
        _doc(1, category="shirt", fit_type="oversize",
             season_fit="summer", fabric_breathability="high"),
        _doc(2, category="shirt", fit_type="oversize",
             season_fit="summer", fabric_breathability="high"),
    ]
    svc, col = _build_service(docs)
    result = svc.query(
        "shirt", "regular", "standart",
        season_fit="all_season", fabric_breathability="medium",
    )
    assert result.status == "ok"
    # Tried strict, drop_breath, drop_season, then category_only → 4 calls.
    assert len(col.calls) == 4
    # Final successful call has only one clause for category.
    assert col.calls[-1] == {"category": {"$eq": "shirt"}}


def test_falls_through_to_no_filter_when_nothing_matches_category():
    docs = [
        _doc(1, category="jacket", fit_type="regular",
             season_fit="winter", fabric_breathability="low"),
    ]
    svc, col = _build_service(docs)
    result = svc.query(
        "shirt", "regular", "standart",
        season_fit="all_season", fabric_breathability="medium",
    )
    # No filter survives — the no-filter tier eventually pulls the jacket.
    # The retrieval gate may then mark it as low_relevance based on cosine,
    # but the where-clause walk must have reached the no_filter step.
    assert col.calls[-1] is None      # last attempt has no filter
    # Walked through all 5 tiers
    assert len(col.calls) == 5
    # The doc was retrieved on the no-filter call
    assert result.retrieval_count >= 1


def test_query_without_optional_filters_still_uses_category_fit_type():
    docs = [
        _doc(1, category="shirt", fit_type="regular",
             season_fit="all_season", fabric_breathability="medium"),
    ]
    svc, col = _build_service(docs)
    svc.query("shirt", "regular", "standart")    # no season / breath
    # Strict tier still applies category+fit_type (season+breath empty are dropped)
    first_where = col.calls[0]
    assert first_where is not None
    keys_in_where = _flatten_where_keys(first_where)
    assert {"category", "fit_type"}.issubset(keys_in_where)


def _flatten_where_keys(where: dict) -> set:
    """Helper: walk Chroma where dialect and return all metadata field names mentioned."""
    out: set[str] = set()
    if "$and" in where:
        for sub in where["$and"]:
            out.update(_flatten_where_keys(sub))
    else:
        for k in where.keys():
            out.add(k)
    return out
