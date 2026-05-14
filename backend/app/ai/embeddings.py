"""
Gemini embedding adapter for ChromaDB.

ChromaDB collections accept any callable matching the EmbeddingFunction
protocol — given a list of strings, return a list of vectors. This module
adapts Google's `genai.embed_content` API into that contract so we can use
Gemini as the embedding model instead of the bundled MiniLM-L6-v2.

Task-type matters for Gemini embeddings: documents and queries must be
embedded under matching but asymmetric task types so retrieval ranks well.
Use task_type="retrieval_document" for ingest and "retrieval_query" for
runtime queries.

Collection name discipline:
  When EMBEDDING_MODEL is unset → MiniLM (vector dim 384) → collection `reviews_v1`.
  When EMBEDDING_MODEL is set   → Gemini  (vector dim 768) → collection `reviews_gemini_v1`.

Keep the two collections separate; mixing vectors from different embedding
models in the same collection produces nonsense similarity scores.
"""

from __future__ import annotations

import logging
import time
import warnings
from typing import List

import numpy as np

# Silence the deprecation FutureWarning from `google.generativeai`. The package
# still works; switching to the new `google.genai` SDK is a larger migration.
# Match by message because Python attributes the warning to the call site, not
# to the deprecated module, so a `module=` filter would never fire.
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    message=".*google\\.generativeai.*has ended.*",
)

logger = logging.getLogger(__name__)

# Gemini free-tier embed cap is ~100 req/min. Sleeping 0.7s between calls keeps
# us at ~85 req/min with margin for jitter and the occasional retry.
_THROTTLE_SECONDS = 0.7
# When the API itself says "retry in N seconds" we honor it once before giving up.
_MAX_RETRIES_ON_429 = 1
_DEFAULT_RETRY_AFTER_SECONDS = 60

MINILM_COLLECTION_NAME = "reviews_v1"
GEMINI_COLLECTION_NAME = "reviews_gemini_v1"


def collection_name_for(embedding_model: str) -> str:
    """Pick the collection name that matches the active embedding model."""
    return GEMINI_COLLECTION_NAME if embedding_model else MINILM_COLLECTION_NAME


def _extract_retry_delay(exc: Exception):
    """Return seconds to wait if exc is a Gemini ResourceExhausted (429), else None.

    The google-api-core ResourceExhausted carries a `RetryInfo` proto detail
    whose `retry_delay.seconds` is the server's hint. Fall back to a default
    if anything in the chain is missing.
    """
    try:
        from google.api_core.exceptions import ResourceExhausted
    except ImportError:
        return None
    if not isinstance(exc, ResourceExhausted):
        return None
    # Try the structured RetryInfo first.
    for detail in getattr(exc, "details", lambda: [])() or []:
        secs = getattr(getattr(detail, "retry_delay", None), "seconds", None)
        if secs:
            return int(secs)
    return _DEFAULT_RETRY_AFTER_SECONDS


class GeminiEmbeddingFunction:
    """ChromaDB-compatible embedding function backed by Google Gemini.

    Parameters
    ----------
    api_key: Google AI Studio API key (same key used for generateContent).
    model:   Embedding model id, e.g. "text-embedding-004".
    task_type: "retrieval_document" for indexing, "retrieval_query" for
               runtime queries. ChromaDB calls the same function for both
               add and query, so a service that does both should hold two
               instances — one per task type — and pass each to the
               right code path.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-004",
        task_type: str = "retrieval_document",
    ) -> None:
        if not api_key:
            raise ValueError("GeminiEmbeddingFunction needs a non-empty api_key")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            import google.generativeai as genai
            genai.configure(api_key=api_key)
        self._genai = genai
        # Gemini accepts both "text-embedding-004" and "models/text-embedding-004".
        self._model = model if model.startswith("models/") else f"models/{model}"
        self._task_type = task_type

    # ChromaDB's EmbeddingFunction contract: __call__(input) -> embeddings.
    # Returns numpy arrays — chromadb >=0.5 calls .tolist() on each vector
    # so plain Python lists trigger AttributeError downstream.
    def __call__(self, input: List[str]):  # noqa: A002 (chroma protocol)
        if not input:
            return []
        vectors = []
        # Per-item is simpler and safer: one bad item won't poison a batch.
        # Queries embed exactly one string; ingest embeds many — proactive
        # throttling keeps us under the free-tier 100 req/min cap.
        for i, text in enumerate(input):
            if i > 0:
                time.sleep(_THROTTLE_SECONDS)
            vectors.append(self._embed_one(text))
        return vectors

    def _embed_one(self, text: str, attempt: int = 0) -> np.ndarray:
        try:
            resp = self._genai.embed_content(
                model=self._model,
                content=text,
                task_type=self._task_type,
            )
            return np.array(resp["embedding"], dtype=np.float32)
        except Exception as exc:
            retry_after = _extract_retry_delay(exc)
            if retry_after is not None and attempt < _MAX_RETRIES_ON_429:
                logger.warning(
                    "gemini_embedding_rate_limited model=%s task=%s sleeping=%ds",
                    self._model, self._task_type, retry_after,
                )
                time.sleep(retry_after + 1)
                return self._embed_one(text, attempt=attempt + 1)
            logger.error(
                "gemini_embedding_failed model=%s task=%s err=%s",
                self._model, self._task_type, type(exc).__name__,
            )
            raise

    # chromadb >= 0.5 may call .name(); return a stable identifier so the
    # collection record can be compared across processes.
    def name(self) -> str:
        return f"gemini-{self._model.split('/')[-1]}-{self._task_type}"
