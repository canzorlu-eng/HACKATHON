"""
UC-06 Review Intelligence Service.

ReviewIntelligenceService accepts any object that exposes the ChromaDB
collection interface (.count(), .query()) so it can be used with:
  - chromadb.HttpClient        (production)
  - chromadb.EphemeralClient   (integration tests)
  - MockChromaClient           (unit tests, no chromadb import needed)

Grounding contract
------------------
Every insight in the returned ReviewIntelligenceResult derives exclusively
from the `themes` metadata field of retrieved documents.  The service
NEVER invents, infers, or extrapolates complaints beyond retrieved evidence.
"""

import logging
from typing import Any

from app.schemas.review import (
    ReviewDocument,
    ReviewInsightSummary,
    ReviewIntelligenceResult,
    ReviewStats,
)

# Theme keyword buckets — used to label whether a reviewer effectively wanted
# a bigger or smaller size, without inventing any data.
_SMALL_CUT_KEYWORDS = ("küçük", "dar", "slim")
_LARGE_CUT_KEYWORDS = ("büyük", "geniş", "bol", "oversize", "rahat kesim")


def _compute_review_stats(items: list[tuple[str, dict, float]]) -> ReviewStats:
    """Aggregate statistics over the relevant reviews. All counts are real."""
    if not items:
        return ReviewStats()

    total = len(items)
    fit_true_count = 0
    resized_up = 0
    resized_down = 0
    theme_counts: dict[str, int] = {}
    size_counts: dict[str, int] = {}

    for _doc, meta, _sim in items:
        fits_true_raw = str(meta.get("fits_true", "True")).lower() == "true"
        if fits_true_raw:
            fit_true_count += 1

        themes_raw = (meta.get("themes") or "").lower()
        themes_list = [t.strip() for t in themes_raw.split(",") if t.strip()]
        for t in themes_list:
            theme_counts[t] = theme_counts.get(t, 0) + 1

        # Resize direction heuristic — fires only when fits_true is False AND
        # the themes contain a directional keyword. Reviewers happy with their
        # purchase don't contribute to either bucket.
        if not fits_true_raw:
            if any(k in themes_raw for k in _SMALL_CUT_KEYWORDS):
                resized_up += 1
            elif any(k in themes_raw for k in _LARGE_CUT_KEYWORDS):
                resized_down += 1

        purchased_size = str(meta.get("purchased_size", "")).strip()
        if purchased_size:
            size_counts[purchased_size] = size_counts.get(purchased_size, 0) + 1

    def pct(n: int) -> int:
        return int(round(n / total * 100))

    top_themes = sorted(theme_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]

    return ReviewStats(
        total_relevant=total,
        fits_true_pct=pct(fit_true_count),
        resized_up_pct=pct(resized_up),
        resized_down_pct=pct(resized_down),
        top_themes=top_themes,
        sample_size_breakdown=size_counts,
    )

logger = logging.getLogger(__name__)

# ── Tuneable thresholds ────────────────────────────────────────────────────

_DEFAULT_MIN_RELEVANCE   = 0.30   # cosine similarity (0=unrelated, 1=identical)
_DEFAULT_DEDUP_THRESHOLD = 0.85   # Jaccard similarity above which a doc is a dup
_DEFAULT_MAX_RESULTS     = 10     # documents fetched from ChromaDB before filtering
_MIN_SUPPORT_TO_REPORT   = 1      # minimum reviews backing a theme before inclusion


# ── Internal helpers ───────────────────────────────────────────────────────

def _jaccard(text_a: str, text_b: str) -> float:
    """Token-level Jaccard similarity (0 = disjoint, 1 = identical)."""
    tokens_a = set(text_a.lower().split())
    tokens_b = set(text_b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def _deduplicate(
    items: list[tuple[str, dict, float]],
    threshold: float = _DEFAULT_DEDUP_THRESHOLD,
) -> list[tuple[str, dict, float]]:
    """
    Remove near-duplicate review documents using pairwise Jaccard similarity.

    Two documents are considered duplicates if their token-level Jaccard
    similarity exceeds `threshold`.  The first occurrence is kept.
    Runs in O(n²) which is fine for n ≤ 20.
    """
    unique: list[tuple[str, dict, float]] = []
    for item in items:
        doc_text = item[0]
        if not any(_jaccard(doc_text, u[0]) >= threshold for u in unique):
            unique.append(item)
    return unique


def _generate_insights(
    items: list[tuple[str, dict, float]],
) -> list[ReviewInsightSummary]:
    """
    Build grounded ReviewInsightSummary objects from retrieved review items.

    Each insight corresponds to exactly one theme label from the `themes`
    metadata field.  No text is generated beyond what is present in the data.
    """
    theme_agg: dict[str, dict[str, Any]] = {}

    for doc_text, meta, similarity in items:
        raw_themes = meta.get("themes") or ""
        sentiment  = meta.get("sentiment", "neutral")
        garment_id = meta.get("garment_id", "")

        for raw_theme in raw_themes.split(","):
            theme = raw_theme.strip()
            if not theme:
                continue

            if theme not in theme_agg:
                theme_agg[theme] = {
                    "count":      0,
                    "sentiment":  sentiment,
                    "evidence":   set(),
                    "total_sim":  0.0,
                }
            theme_agg[theme]["count"]     += 1
            theme_agg[theme]["total_sim"] += similarity
            if garment_id:
                theme_agg[theme]["evidence"].add(garment_id)

    # Sort: highest support count first, break ties by avg relevance
    ranked = sorted(
        theme_agg.items(),
        key=lambda kv: (
            kv[1]["count"],
            kv[1]["total_sim"] / max(kv[1]["count"], 1),
        ),
        reverse=True,
    )

    insights = []
    for theme, data in ranked[:6]:   # cap at 6 insights per query
        if data["count"] < _MIN_SUPPORT_TO_REPORT:
            continue
        insights.append(
            ReviewInsightSummary(
                theme_tr=theme,
                support_count=data["count"],
                sentiment=data["sentiment"],
                is_grounded=True,
                evidence_refs=sorted(data["evidence"])[:3],
                avg_relevance=round(
                    data["total_sim"] / max(data["count"], 1), 3
                ),
            )
        )
    return insights


# ── Service ────────────────────────────────────────────────────────────────

class ReviewIntelligenceService:
    """
    UC-06 Review Intelligence: retrieve, filter, deduplicate, summarise.

    Parameters
    ----------
    chroma_client:
        Any object with a ``get_or_create_collection(name, **kw)`` method.
    collection_name:
        ChromaDB collection to query.  Default: ``reviews_v1``.
    """

    def __init__(
        self,
        chroma_client: Any,
        collection_name: str = "reviews_v1",
        embedding_function: Any = None,
    ) -> None:
        self._client             = chroma_client
        self._collection_name    = collection_name
        self._embedding_function = embedding_function
        self._col                = None   # lazy-loaded

    def _collection(self):
        if self._col is None:
            kwargs = {
                "name": self._collection_name,
                "metadata": {"hnsw:space": "cosine"},
            }
            if self._embedding_function is not None:
                kwargs["embedding_function"] = self._embedding_function
            self._col = self._client.get_or_create_collection(**kwargs)
        return self._col

    # ------------------------------------------------------------------

    def query(
        self,
        category: str,
        fit_type: str,
        brand_tendency: str,
        *,
        min_relevance: float = _DEFAULT_MIN_RELEVANCE,
        max_results:   int   = _DEFAULT_MAX_RESULTS,
        dedup_threshold: float = _DEFAULT_DEDUP_THRESHOLD,
    ) -> ReviewIntelligenceResult:
        """
        Run the full RAG pipeline for review intelligence.

        Returns a ReviewIntelligenceResult with status:
          "empty"          – collection has no documents
          "low_relevance"  – documents found but none pass the relevance gate
          "ok"             – at least one grounded insight produced
        """
        col = self._collection()

        # ── 1. Empty collection ──────────────────────────────────────
        total_docs = col.count()
        if total_docs == 0:
            logger.info("review_service status=empty collection=%s", self._collection_name)
            return ReviewIntelligenceResult(
                status="empty",
                message_tr="Henüz yeterli kullanıcı yorumu bulunmuyor.",
            )

        # ── 2. Query ─────────────────────────────────────────────────
        n = min(max_results, total_docs)
        query_text = (
            f"{category} {fit_type} {brand_tendency} "
            "beden uyum kalıp kesiyor"
        )
        raw = col.query(
            query_texts=[query_text],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )

        docs      = (raw.get("documents") or [[]])[0]
        metas     = (raw.get("metadatas") or [[]])[0]
        distances = (raw.get("distances")  or [[]])[0]

        # ── 3. Relevance filter ──────────────────────────────────────
        # ChromaDB cosine distance: 0 = identical, 2 = opposite.
        # Similarity = 1 − distance  (clamped to [0, 1]).
        relevant = [
            (doc, meta, max(0.0, min(1.0, 1.0 - dist)))
            for doc, meta, dist in zip(docs, metas, distances)
            if max(0.0, min(1.0, 1.0 - dist)) >= min_relevance
        ]

        if not relevant:
            logger.info(
                "review_service status=low_relevance retrieved=%d min_sim=%.2f",
                len(docs), min_relevance,
            )
            return ReviewIntelligenceResult(
                status="low_relevance",
                retrieval_count=len(docs),
                message_tr=(
                    "Bulunan yorumlar bu ürün tipiyle yeterince ilgili değil. "
                    "Genel öneriler esas alındı."
                ),
            )

        # ── 4. Deduplicate ───────────────────────────────────────────
        unique = _deduplicate(relevant, threshold=dedup_threshold)

        # ── 5. Generate grounded insights ────────────────────────────
        insights = _generate_insights(unique)

        # ── 6. Build ReviewDocument list (for possible future audit) ─
        review_docs = [
            ReviewDocument(
                review_id=meta.get("garment_id", f"doc_{i}"),
                garment_id=meta.get("garment_id", ""),
                review_text=doc,
                purchased_size=meta.get("purchased_size", ""),
                fits_true=meta.get("fits_true", "True").lower() == "true",
                themes=[t.strip() for t in (meta.get("themes") or "").split(",") if t.strip()],
                sentiment=meta.get("sentiment", "neutral"),
                relevance_score=max(0.0, min(1.0, 1.0 - dist)),
            )
            for i, (doc, meta, dist) in enumerate(
                zip(docs, metas, distances)
                )
            if max(0.0, min(1.0, 1.0 - dist)) >= min_relevance
        ]

        logger.info(
            "review_service status=ok retrieved=%d relevant=%d unique=%d insights=%d",
            len(docs), len(relevant), len(unique), len(insights),
        )

        return ReviewIntelligenceResult(
            status="ok",
            insights=insights,
            retrieval_count=len(docs),
            unique_count=len(unique),
            relevant_count=len(relevant),
            stats=_compute_review_stats(unique),
        )


# ── Demo seed data ─────────────────────────────────────────────────────────

_DEMO_DOCS = [
    {
        "id": "demo_1",
        "text": "Kıyafet beden konusunda sorun çıkarmadı, normal kalıp.",
        "meta": {"themes": "beden uyumu", "sentiment": "positive",
                 "garment_id": "g_demo_1", "purchased_size": "M", "fits_true": "True"},
    },
    {
        "id": "demo_2",
        "text": "Kumaş kalitesi çok iyiydi, yumuşak ve rahat.",
        "meta": {"themes": "kumaş kalitesi", "sentiment": "positive",
                 "garment_id": "g_demo_2", "purchased_size": "M", "fits_true": "True"},
    },
    {
        "id": "demo_3",
        "text": "Beden biraz küçük geldi, bir üst beden almak gerekti.",
        "meta": {"themes": "beden uyumu, dar kesim", "sentiment": "negative",
                 "garment_id": "g_demo_3", "purchased_size": "L", "fits_true": "False"},
    },
    {
        "id": "demo_4",
        "text": "Kol boyu biraz kısa geldi, dikkat etmek lazım.",
        "meta": {"themes": "kol boyu", "sentiment": "neutral",
                 "garment_id": "g_demo_4", "purchased_size": "M", "fits_true": "False"},
    },
    {
        "id": "demo_5",
        "text": "Harika bir ürün, tam kalıbında.",
        "meta": {"themes": "beden uyumu", "sentiment": "positive",
                 "garment_id": "g_demo_5", "purchased_size": "S", "fits_true": "True"},
    },
]


class _DemoCollection:
    """
    Pure-Python ChromaDB collection stub for DEMO_MODE.

    Avoids importing chromadb so demo startup does not trigger the
    79 MB MiniLM ONNX download. Returns the seeded demo docs with
    fixed similarity scores (Jaccard-based) so the existing relevance
    filter still works.
    """

    def __init__(self, docs: list[dict]) -> None:
        self._docs = docs

    def count(self) -> int:
        return len(self._docs)

    def query(self, query_texts, n_results, include):  # noqa: ARG002
        query = (query_texts[0] if query_texts else "").lower()
        q_tokens = set(query.split())
        scored: list[tuple[float, dict]] = []
        for d in self._docs:
            text_tokens = set(d["text"].lower().split())
            theme_tokens = set((d["meta"].get("themes") or "").lower().replace(",", " ").split())
            tokens = text_tokens | theme_tokens
            overlap = len(q_tokens & tokens)
            denom = max(len(q_tokens | tokens), 1)
            sim = max(0.35, min(0.95, 0.40 + (overlap / denom) * 0.55))
            scored.append((sim, d))
        scored.sort(key=lambda kv: kv[0], reverse=True)
        sample = scored[: min(n_results, len(scored))]
        return {
            "documents": [[d["text"] for _, d in sample]],
            "metadatas": [[d["meta"] for _, d in sample]],
            "distances": [[1.0 - sim for sim, _ in sample]],
        }


def _make_demo_service() -> ReviewIntelligenceService:
    """Build an in-process review service seeded with demo documents.

    Uses a pure-Python collection stub (no chromadb dependency) to keep
    DEMO_MODE startup instant — the real ChromaDB embedding model would
    otherwise download ~79 MB on first query and overrun the pipeline timeout.
    """
    col = _DemoCollection(_DEMO_DOCS)
    service = ReviewIntelligenceService.__new__(ReviewIntelligenceService)
    service._client = None
    service._collection_name = "reviews_v1"
    service._col = col
    return service


# ── Factory ────────────────────────────────────────────────────────────────

def get_review_service() -> ReviewIntelligenceService | None:
    """
    Return a ReviewIntelligenceService.

    - DEMO_MODE=true → returns an in-memory EphemeralClient seeded with demo docs.
    - Otherwise → connects to ChromaDB HttpClient; returns None on failure.
    """
    from app.config import get_settings
    s = get_settings()

    if s.demo_mode:
        try:
            return _make_demo_service()
        except Exception as exc:
            logger.debug("demo_review_service_failed: %s", type(exc).__name__)
            return None

    try:
        import chromadb
        from app.ai.embeddings import (
            GeminiEmbeddingFunction,
            collection_name_for,
        )

        client = chromadb.HttpClient(
            host=s.chroma_host,
            port=int(s.chroma_port),
            settings=chromadb.config.Settings(anonymized_telemetry=False),
        )
        client.heartbeat()   # fast fail if server is down

        # If EMBEDDING_MODEL is set, route queries to Gemini's embedding API
        # and target the gemini-specific collection. Otherwise stay on the
        # default MiniLM-backed `reviews_v1` collection.
        embedding_fn = None
        if s.embedding_model and s.gemini_api_key:
            embedding_fn = GeminiEmbeddingFunction(
                api_key=s.gemini_api_key,
                model=s.embedding_model,
                task_type="retrieval_query",
            )
            logger.info(
                "review_service using Gemini embeddings model=%s",
                s.embedding_model,
            )

        return ReviewIntelligenceService(
            client,
            collection_name=collection_name_for(s.embedding_model),
            embedding_function=embedding_fn,
        )
    except Exception as exc:
        logger.debug("review_service unavailable: %s", type(exc).__name__)
        return None
