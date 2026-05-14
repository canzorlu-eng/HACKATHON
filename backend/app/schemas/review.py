"""
UC-06 Review Intelligence schemas.

All user-facing strings are Turkish.
is_grounded is always True — the service only produces claims
that are directly supported by retrieved review metadata.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class ReviewDocument(BaseModel):
    """A single retrieved review document with its relevance score."""
    review_id: str
    garment_id: str
    review_text: str
    purchased_size: str
    fits_true: bool
    themes: list[str]
    sentiment: str
    relevance_score: float = Field(ge=0.0, le=1.0)


class ReviewInsightSummary(BaseModel):
    """
    One grounded insight derived from retrieved reviews.

    is_grounded is always True: the theme_tr value comes directly from the
    themes metadata field of retrieved documents — it is never inferred or
    invented beyond the evidence.
    """
    theme_tr: str                           # Turkish theme label from metadata
    support_count: int = Field(ge=1)        # how many reviews mention this theme
    sentiment: str                          # positive | negative | neutral | warning
    is_grounded: bool = True                # invariant: always True
    evidence_refs: list[str] = Field(default_factory=list)  # garment IDs (proof)
    avg_relevance: float = Field(default=0.0, ge=0.0, le=1.0)

    def to_turkish_sentence(self) -> str:
        """Format as a concise Turkish summary sentence."""
        n = self.support_count
        theme = self.theme_tr

        prefix_map = {
            "positive":  "Kullanıcılar memnun:",
            "negative":  "Kullanıcılar dikkat çekiyor:",
            "warning":   "Önemli uyarı:",
            "neutral":   "Kullanıcı yorumlarına göre:",
        }
        prefix = prefix_map.get(self.sentiment, "Kullanıcı yorumlarına göre:")
        count_note = f"({n} yorum)" if n > 1 else "(1 yorum)"
        return f"{prefix} {theme} {count_note}"


RetrievalStatus = Literal["ok", "empty", "low_relevance", "fallback", "error"]


class ReviewStats(BaseModel):
    """Aggregated statistics computed over the relevant retrieved reviews.

    These are real counts pulled from the review corpus metadata — never
    invented. The narrative composer is allowed to quote these numbers
    verbatim in the detailed explanation.
    """
    total_relevant: int = 0          # how many reviews matched the relevance gate
    fits_true_pct: int = 0           # % of reviewers who reported the garment fit as expected
    resized_up_pct: int = 0          # % who effectively wanted to size up (fits_true=False + small-cut theme)
    resized_down_pct: int = 0        # % who effectively wanted to size down (fits_true=False + large-cut theme)
    top_themes: list[tuple[str, int]] = Field(default_factory=list)  # [(theme, count), ...] sorted desc
    sample_size_breakdown: dict[str, int] = Field(default_factory=dict)  # purchased_size → count


class ReviewIntelligenceResult(BaseModel):
    """Full output of the UC-06 Review Intelligence pipeline step."""

    status: RetrievalStatus
    insights: list[ReviewInsightSummary] = Field(default_factory=list)
    retrieval_count: int = 0      # raw docs returned by ChromaDB
    unique_count: int = 0         # after deduplication
    relevant_count: int = 0       # after relevance filtering
    message_tr: Optional[str] = None  # Turkish status message (set on non-ok paths)
    stats: Optional[ReviewStats] = None  # only present when status == "ok"

    @property
    def community_insights_tr(self) -> list[str]:
        """
        Turkish sentences ready for the final response.

        Returns a single no-data message when no grounded insights exist.
        """
        if not self.insights:
            return [self.message_tr or "Henüz yeterli kullanıcı yorumu bulunmuyor."]
        return [ins.to_turkish_sentence() for ins in self.insights]

    @property
    def as_pipeline_dicts(self) -> list[dict]:
        """Serialise insights to plain dicts for LangGraph state (must be JSON-safe)."""
        return [ins.model_dump() for ins in self.insights]
