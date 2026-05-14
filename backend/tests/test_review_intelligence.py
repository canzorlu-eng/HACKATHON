"""
Tests for UC-06 Review Intelligence.

Uses MockChromaClient / MockCollection — no ChromaDB process required.
"""

import pytest

from app.schemas.review import ReviewInsightSummary, ReviewIntelligenceResult
from app.services.review_service import (
    ReviewIntelligenceService,
    _deduplicate,
    _generate_insights,
)


# ── Mock ChromaDB helpers ─────────────────────────────────────────────────────

class MockCollection:
    """Minimal ChromaDB collection stub."""

    def __init__(self, docs: list[dict]):
        """
        Each element in `docs` is:
          {"text": str, "meta": dict, "distance": float}
        """
        self._docs = docs

    def count(self) -> int:
        return len(self._docs)

    def query(self, query_texts, n_results, include):  # noqa: ARG002
        n = min(n_results, len(self._docs))
        sample = self._docs[:n]
        return {
            "documents": [[d["text"] for d in sample]],
            "metadatas": [[d["meta"] for d in sample]],
            "distances": [[d["distance"] for d in sample]],
        }


class MockChromaClient:
    """Minimal ChromaDB client stub."""

    def __init__(self, docs: list[dict] | None = None):
        self._docs = docs or []

    def get_or_create_collection(self, name, **kwargs):  # noqa: ARG002
        return MockCollection(self._docs)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_doc(
    text: str = "iyi ürün",
    themes: str = "beden uyumu",
    sentiment: str = "positive",
    garment_id: str = "g001",
    distance: float = 0.2,          # similarity = 0.8 (well above 0.30 threshold)
) -> dict:
    return {
        "text": text,
        "meta": {
            "themes": themes,
            "sentiment": sentiment,
            "garment_id": garment_id,
            "purchased_size": "M",
            "fits_true": "True",
        },
        "distance": distance,
    }


# ── Unit tests: _deduplicate ──────────────────────────────────────────────────

class TestDeduplicate:
    def test_identical_texts_are_deduplicated(self):
        items = [
            ("aynı metin var", {}, 0.9),
            ("aynı metin var", {}, 0.8),
        ]
        result = _deduplicate(items, threshold=0.85)
        assert len(result) == 1

    def test_distinct_texts_all_kept(self):
        items = [
            ("kısa kollu tişört", {}, 0.9),
            ("uzun etek dar kesim", {}, 0.8),
            ("büyük beden mont", {}, 0.7),
        ]
        result = _deduplicate(items, threshold=0.85)
        assert len(result) == 3

    def test_near_duplicate_above_threshold_removed(self):
        # High Jaccard overlap → removed
        items = [
            ("beden küçük kalıyor dar", {}, 0.9),
            ("beden küçük kalıyor dar kesiyor", {}, 0.8),
        ]
        result = _deduplicate(items, threshold=0.60)
        assert len(result) == 1

    def test_empty_input_returns_empty(self):
        assert _deduplicate([], threshold=0.85) == []

    def test_first_occurrence_kept(self):
        items = [
            ("ilk metin", {}, 0.95),
            ("ilk metin", {}, 0.80),
        ]
        result = _deduplicate(items)
        assert result[0][2] == 0.95  # highest-scored first doc retained


# ── Unit tests: _generate_insights ───────────────────────────────────────────

class TestGenerateInsights:
    def _item(self, themes: str, sentiment: str = "neutral", garment_id: str = "g1", sim: float = 0.8):
        return ("review text", {"themes": themes, "sentiment": sentiment, "garment_id": garment_id}, sim)

    def test_basic_insight_creation(self):
        items = [self._item("beden uyumu")]
        insights = _generate_insights(items)
        assert len(insights) == 1
        assert insights[0].theme_tr == "beden uyumu"
        assert insights[0].support_count == 1
        assert insights[0].is_grounded is True

    def test_multiple_themes_split_by_comma(self):
        items = [self._item("beden uyumu, kumaş kalitesi")]
        insights = _generate_insights(items)
        themes = {i.theme_tr for i in insights}
        assert "beden uyumu" in themes
        assert "kumaş kalitesi" in themes

    def test_support_count_aggregated_across_docs(self):
        items = [
            self._item("beden uyumu", garment_id="g1"),
            self._item("beden uyumu", garment_id="g2"),
            self._item("beden uyumu", garment_id="g3"),
        ]
        insights = _generate_insights(items)
        assert insights[0].support_count == 3

    def test_insights_capped_at_six(self):
        themes_list = ["tema1", "tema2", "tema3", "tema4", "tema5", "tema6", "tema7"]
        items = [self._item(t) for t in themes_list]
        insights = _generate_insights(items)
        assert len(insights) <= 6

    def test_evidence_refs_populated(self):
        items = [
            self._item("beden uyumu", garment_id="g1"),
            self._item("beden uyumu", garment_id="g2"),
        ]
        insights = _generate_insights(items)
        assert len(insights[0].evidence_refs) > 0

    def test_is_grounded_always_true(self):
        items = [self._item("herhangi tema")]
        for insight in _generate_insights(items):
            assert insight.is_grounded is True

    def test_empty_theme_strings_ignored(self):
        items = [self._item("  ,  , ")]
        insights = _generate_insights(items)
        assert insights == []

    def test_grounded_themes_only_from_metadata(self):
        """All theme_tr values must appear verbatim in the themes metadata — no invention."""
        source_themes = {"beden uyumu", "kumaş kalitesi", "dar kesim"}
        items = [self._item(", ".join(source_themes))]
        insights = _generate_insights(items)
        for ins in insights:
            assert ins.theme_tr in source_themes, (
                f"'{ins.theme_tr}' was invented — not in source metadata"
            )


# ── Service tests: status paths ───────────────────────────────────────────────

class TestReviewIntelligenceServiceEmpty:
    def test_empty_collection_returns_empty_status(self):
        service = ReviewIntelligenceService(MockChromaClient(docs=[]))
        result = service.query("shirt", "regular", "standart")
        assert result.status == "empty"
        assert result.insights == []
        assert result.message_tr is not None

    def test_empty_community_insights_tr_returns_fallback_string(self):
        service = ReviewIntelligenceService(MockChromaClient(docs=[]))
        result = service.query("shirt", "regular", "standart")
        tr = result.community_insights_tr
        assert len(tr) == 1
        assert tr[0]  # non-empty string


class TestReviewIntelligenceServiceLowRelevance:
    def test_high_distance_triggers_low_relevance(self):
        # distance=0.85 → similarity=0.15, below min_relevance=0.30
        docs = [_make_doc(distance=0.85)]
        service = ReviewIntelligenceService(MockChromaClient(docs=docs))
        result = service.query("shirt", "regular", "standart")
        assert result.status == "low_relevance"
        assert result.insights == []
        assert result.retrieval_count > 0

    def test_low_relevance_message_is_turkish(self):
        docs = [_make_doc(distance=0.85)]
        service = ReviewIntelligenceService(MockChromaClient(docs=docs))
        result = service.query("shirt", "regular", "standart")
        assert result.message_tr
        # Basic Turkish character check
        assert any(c in result.message_tr for c in ("ı", "ğ", "ü", "ş", "ö", "ç", "İ", " "))


class TestReviewIntelligenceServiceNormal:
    def test_ok_status_with_relevant_docs(self):
        docs = [_make_doc(distance=0.15)]  # similarity=0.85
        service = ReviewIntelligenceService(MockChromaClient(docs=docs))
        result = service.query("shirt", "regular", "standart")
        assert result.status == "ok"
        assert len(result.insights) >= 1

    def test_retrieval_counts_populated(self):
        docs = [_make_doc(distance=0.15), _make_doc(distance=0.20)]
        service = ReviewIntelligenceService(MockChromaClient(docs=docs))
        result = service.query("shirt", "regular", "standart")
        assert result.retrieval_count == 2
        assert result.relevant_count >= 1
        assert result.unique_count >= 1

    def test_community_insights_tr_non_empty_on_ok(self):
        docs = [_make_doc(distance=0.15)]
        service = ReviewIntelligenceService(MockChromaClient(docs=docs))
        result = service.query("shirt", "regular", "standart")
        tr = result.community_insights_tr
        assert len(tr) >= 1
        assert all(isinstance(s, str) and s for s in tr)

    def test_as_pipeline_dicts_serializable(self):
        docs = [_make_doc(distance=0.15)]
        service = ReviewIntelligenceService(MockChromaClient(docs=docs))
        result = service.query("shirt", "regular", "standart")
        dicts = result.as_pipeline_dicts
        assert isinstance(dicts, list)
        for d in dicts:
            assert isinstance(d, dict)
            assert "theme_tr" in d
            assert "support_count" in d
            assert "is_grounded" in d


class TestReviewIntelligenceServiceDedup:
    def test_near_duplicate_docs_deduplicated(self):
        # Two nearly identical docs — only one insight batch should come through
        doc_text = "Bu ürün beden konusunda sorun çıkarıyor dar dar dar"
        docs = [
            {"text": doc_text, "meta": {"themes": "dar kesim", "sentiment": "negative",
                                         "garment_id": "g1", "purchased_size": "M", "fits_true": "False"},
             "distance": 0.15},
            {"text": doc_text, "meta": {"themes": "dar kesim", "sentiment": "negative",
                                         "garment_id": "g1", "purchased_size": "M", "fits_true": "False"},
             "distance": 0.16},
        ]
        service = ReviewIntelligenceService(MockChromaClient(docs=docs))
        result = service.query("shirt", "slim-cut", "standart")
        assert result.status == "ok"
        # unique_count must be less than retrieval_count due to dedup
        assert result.unique_count <= result.relevant_count


class TestGroundingInvariant:
    def test_all_insights_are_grounded(self):
        """is_grounded MUST be True on every insight the service produces."""
        docs = [
            _make_doc(themes="beden uyumu, dar kesim", distance=0.10),
            _make_doc(themes="kumaş kalitesi", garment_id="g2", distance=0.12),
        ]
        service = ReviewIntelligenceService(MockChromaClient(docs=docs))
        result = service.query("shirt", "regular", "standart")
        assert result.status == "ok"
        for insight in result.insights:
            assert insight.is_grounded is True

    def test_no_invented_themes(self):
        """Every theme_tr in insights must originate from the metadata themes field."""
        source_themes = {"beden uyumu", "dar kesim", "kumaş kalitesi"}
        docs = [
            {
                "text": "yorum metni",
                "meta": {
                    "themes": ", ".join(source_themes),
                    "sentiment": "negative",
                    "garment_id": "g1",
                    "purchased_size": "M",
                    "fits_true": "False",
                },
                "distance": 0.10,
            }
        ]
        service = ReviewIntelligenceService(MockChromaClient(docs=docs))
        result = service.query("shirt", "regular", "standart")
        for insight in result.insights:
            assert insight.theme_tr in source_themes, (
                f"Insight theme '{insight.theme_tr}' not in source metadata — grounding violated"
            )


# ── Pipeline integration test ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_review_retriever_node_fallback_when_no_service(monkeypatch):
    """When get_review_service() returns None, node must use fallback insights."""
    from app.ai.nodes import review_retriever_node

    monkeypatch.setattr(
        "app.services.review_service.get_review_service",
        lambda: None,
    )

    state = {
        "garment_analysis": {
            "category": "shirt",
            "fit_type": "regular",
            "brand_sizing_tendency": "standart",
        }
    }
    result = review_retriever_node(state)
    assert "review_insights" in result
    assert isinstance(result["review_insights"], list)
    assert len(result["review_insights"]) > 0
    assert result.get("review_retrieval_status") == "fallback"


@pytest.mark.asyncio
async def test_review_retriever_node_uses_service_ok(monkeypatch):
    """When service returns ok, node returns service insights."""
    from app.ai.nodes import review_retriever_node
    from app.services.review_service import ReviewIntelligenceService

    mock_service = ReviewIntelligenceService(
        MockChromaClient(docs=[_make_doc(distance=0.15)])
    )
    monkeypatch.setattr(
        "app.services.review_service.get_review_service",
        lambda: mock_service,
    )

    state = {
        "garment_analysis": {
            "category": "shirt",
            "fit_type": "regular",
            "brand_sizing_tendency": "standart",
        }
    }
    result = review_retriever_node(state)
    assert result.get("review_retrieval_status") == "ok"
    assert isinstance(result["review_insights"], list)


@pytest.mark.asyncio
async def test_review_retriever_node_brand_fallback_inserts_warning(monkeypatch):
    """Small-brand fallback must prepend a beden büyük warning insight."""
    from app.ai.nodes import review_retriever_node

    # Force the service unavailable — otherwise a host-side ChromaDB
    # running for live work would let this test connect for real and the
    # node would return status="ok" instead of "fallback".
    monkeypatch.setattr(
        "app.services.review_service.get_review_service",
        lambda: None,
    )

    state = {
        "garment_analysis": {
            "category": "shirt",
            "fit_type": "regular",
            "brand_sizing_tendency": "küçük kalıplı",
        }
    }

    result = review_retriever_node(state)
    assert result["review_retrieval_status"] == "fallback"
    themes = [ins.get("theme", "") for ins in result["review_insights"]]
    assert any("büyük" in t for t in themes)
