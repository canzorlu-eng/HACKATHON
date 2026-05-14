"""LangGraph pipeline state schema."""

from typing import Optional
from typing_extensions import TypedDict


class PipelineState(TypedDict, total=False):
    # ---- Inputs (always set before pipeline runs) ----
    analysis_id: str
    user_id: str
    height_cm: int
    weight_kg: int
    fit_preference: str
    body_image_ref: Optional[str]   # None when user has no body image
    garment_image_ref: str
    storage_dir: str                # image_storage_dir value for reading bytes

    # ---- Node outputs ----
    intent_valid: bool
    intent_error: Optional[str]

    body_analysis: Optional[dict]   # keys: silhouette_type, fit_tendency, confidence, …
    garment_analysis: Optional[dict] # keys: category, fit_type, fabric_cues, confidence, …

    review_insights: list           # list of dicts: theme, count, sentiment
    review_retrieval_status: str    # "ok" | "empty" | "low_relevance" | "fallback" | "error"
    review_stats: Optional[dict]    # aggregated %s from review corpus (see ReviewStats)

    recommendation: Optional[dict]  # recommended_size, confidence, explanation_tr, uncertainty_tr
    risk_evaluation: Optional[dict] # risk_level, risk_factors, risk_score, confidence
    detailed_explanation_tr: Optional[str]  # multi-sentence narrative from compose_narrative

    final_response: Optional[dict]  # full Turkish-formatted output returned to the user
    pipeline_error: Optional[str]   # set on unexpected failures; pipeline still returns partial state
