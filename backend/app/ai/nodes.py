"""
LangGraph node functions for the HIWALOY fit analysis pipeline.

Node execution order:
  intent_validator → parallel_analyzer → review_retriever
  → recommendation_generator → risk_evaluator → turkish_formatter
"""

import asyncio
import logging
from typing import Optional

from app.ai.state import PipelineState
from app.services.image_store import read_image_bytes

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]


def _size_from_bmi(bmi: float, height_cm: int) -> str:
    if bmi < 17.5:
        return "XS"
    if bmi < 20.5:
        return "S" if height_cm <= 170 else "M"
    if bmi < 24.0:
        return "M" if height_cm <= 178 else "L"
    if bmi < 27.5:
        return "L" if height_cm <= 183 else "XL"
    if bmi < 31.0:
        return "XL"
    return "XXL"


def _shift_size(size: str, delta: int) -> str:
    i = _SIZES.index(size) + delta
    return _SIZES[max(0, min(len(_SIZES) - 1, i))]


_FIT_TYPE_DELTA = {"slim-cut": -1, "regular": 0, "relaxed": 1, "oversize": 2}
_USER_PREF_DELTA = {"slim": -1, "regular": 0, "relaxed": 1, "oversize": 2}
_TENDENCY_DELTA  = {"dar taraflı": -1, "standart": 0, "geniş taraflı": 1}
_BRAND_DELTA     = {"küçük kalıplı": 1, "standart": 0, "büyük kalıplı": -1}


# ---------------------------------------------------------------------------
# Node 1: Intent validator
# ---------------------------------------------------------------------------

def intent_validator_node(state: PipelineState) -> dict:
    """Sanity-check that all required inputs are present before AI work begins."""
    errors: list[str] = []

    garment_ref = state.get("garment_image_ref", "")
    if not garment_ref:
        errors.append("Kıyafet görseli eksik.")

    h = state.get("height_cm", 0)
    if not (50 <= h <= 300):
        errors.append(f"Boy değeri geçersiz: {h}.")

    w = state.get("weight_kg", 0)
    if not (20 <= w <= 500):
        errors.append(f"Kilo değeri geçersiz: {w}.")

    if errors:
        return {"intent_valid": False, "intent_error": " ".join(errors)}
    return {"intent_valid": True, "intent_error": None}


# ---------------------------------------------------------------------------
# Node 2: Parallel body + garment analyser (takes AI client via closure)
# ---------------------------------------------------------------------------

def make_analyzer_node(ai_client):
    """Returns a LangGraph-compatible async node that injects ai_client."""

    async def analyzer_node(state: PipelineState) -> dict:
        storage_dir = state.get("storage_dir", "")

        garment_bytes = read_image_bytes(
            state.get("garment_image_ref", ""), storage_dir=storage_dir
        )

        body_ref = state.get("body_image_ref")
        body_bytes: Optional[bytes] = None
        if body_ref:
            body_bytes = read_image_bytes(body_ref, storage_dir=storage_dir)

        body_task = ai_client.analyze_body(
            body_bytes,
            state.get("height_cm", 170),
            state.get("weight_kg", 65),
            state.get("fit_preference", "regular"),
        )
        garment_task = ai_client.analyze_garment(garment_bytes)

        body_result, garment_result = await asyncio.gather(body_task, garment_task)
        logger.info(
            "ai_analysis_done body_conf=%.2f garment_conf=%.2f",
            body_result.get("confidence", 0),
            garment_result.get("confidence", 0),
        )
        return {"body_analysis": body_result, "garment_analysis": garment_result}

    return analyzer_node


# ---------------------------------------------------------------------------
# Node 3: Review retriever (UC-06 ReviewIntelligenceService with fallback)
# ---------------------------------------------------------------------------

_FALLBACK_INSIGHTS = [
    {"theme": "beden tablosunu kontrol edin", "count": 12, "sentiment": "neutral"},
    {"theme": "kumaş kalitesi iyi", "count": 8, "sentiment": "positive"},
]


def review_retriever_node(state: PipelineState) -> dict:
    """
    Query ChromaDB via ReviewIntelligenceService for grounded review insights.

    Falls back to curated placeholder insights when the service is unavailable
    or returns no relevant results.  The retrieval status is stored in
    ``review_retrieval_status`` so downstream nodes and tests can inspect it.
    """
    from app.services.review_service import get_review_service

    garment  = state.get("garment_analysis") or {}
    category = garment.get("category", "")
    fit_type = garment.get("fit_type", "regular")
    brand    = garment.get("brand_sizing_tendency", "standart")

    service = get_review_service()

    if service is not None:
        try:
            result = service.query(category, fit_type, brand)
            if result.status == "ok":
                logger.info(
                    "review_retriever source=chroma insights=%d category=%s",
                    len(result.insights), category,
                )
                return {
                    "review_insights": result.as_pipeline_dicts,
                    "review_retrieval_status": result.status,
                }
            # Empty or low-relevance — fall through to fallback
            logger.info(
                "review_retriever status=%s — using fallback insights", result.status,
            )
        except Exception as exc:
            logger.debug("review_retriever service_error: %s", type(exc).__name__)

    # ── Fallback: curated placeholder insights ────────────────────────────
    insights = list(_FALLBACK_INSIGHTS)
    if brand == "küçük kalıplı":
        insights.insert(0, {"theme": "bir beden büyük alınmasını öneriyor", "count": 15, "sentiment": "warning"})
    elif brand == "büyük kalıplı":
        insights.insert(0, {"theme": "bir beden küçük alınmasını öneriyor", "count": 10, "sentiment": "warning"})

    logger.info(
        "review_retriever source=fallback insights=%d category=%s",
        len(insights), category,
    )
    return {
        "review_insights": insights,
        "review_retrieval_status": "fallback",
    }


# ---------------------------------------------------------------------------
# Node 4: Recommendation generator (deterministic)
# ---------------------------------------------------------------------------

def recommendation_generator_node(state: PipelineState) -> dict:
    body    = state.get("body_analysis")    or {}
    garment = state.get("garment_analysis") or {}

    height_cm   = state.get("height_cm", 170)
    weight_kg   = state.get("weight_kg", 65)
    user_pref   = state.get("fit_preference", "regular")
    has_body_img = bool(state.get("body_image_ref"))

    bmi = weight_kg / ((height_cm / 100) ** 2)
    base_size = _size_from_bmi(bmi, height_cm)

    fit_tendency = body.get("fit_tendency", "standart")
    fit_type     = garment.get("fit_type", "regular")
    brand        = garment.get("brand_sizing_tendency", "standart")

    delta  = _TENDENCY_DELTA.get(fit_tendency, 0)
    delta += _FIT_TYPE_DELTA.get(fit_type, 0) - _USER_PREF_DELTA.get(user_pref, 0)
    delta += _BRAND_DELTA.get(brand, 0)
    recommended = _shift_size(base_size, delta)

    body_conf    = float(body.get("confidence", 0.5))
    garment_conf = float(garment.get("confidence", 0.5))
    reviews      = state.get("review_insights") or []
    review_boost = min(0.08, len(reviews) * 0.02)
    confidence   = body_conf * 0.55 + garment_conf * 0.40 + review_boost
    if not has_body_img:
        confidence *= 0.78  # penalise for missing body image

    body_uncertainty    = body.get("uncertainty_reason", "")
    garment_uncertainty = garment.get("uncertainty_reason", "")

    # Turkish explanation
    brand_note = ""
    if brand == "küçük kalıplı":
        brand_note = " Marka küçük kalıplı olduğundan bir beden büyük alınması önerildi."
    elif brand == "büyük kalıplı":
        brand_note = " Marka büyük kalıplı olduğundan bir beden küçük alınması önerildi."

    explanation = (
        f"Beden ölçüleriniz ve kıyafetin {fit_type} kesimine göre "
        f"{recommended} beden önerilmektedir.{brand_note}"
    )

    uncertainty_parts = [p for p in [body_uncertainty, garment_uncertainty] if p]
    uncertainty = " ".join(uncertainty_parts) if uncertainty_parts else "Yeterli veri mevcut."

    return {
        "recommendation": {
            "recommended_size": recommended,
            "confidence": round(confidence, 3),
            "explanation_tr": explanation,
            "uncertainty_tr": uncertainty,
        }
    }


# ---------------------------------------------------------------------------
# Node 5: Risk evaluator
# ---------------------------------------------------------------------------

_RISK_LEVEL_LABELS = {
    "low":    "Düşük Risk",
    "medium": "Orta Risk",
    "high":   "Yüksek Risk",
}


def risk_evaluator_node(state: PipelineState) -> dict:
    rec     = state.get("recommendation")    or {}
    garment = state.get("garment_analysis")  or {}
    reviews = state.get("review_insights")   or []

    confidence = float(rec.get("confidence", 0.5))
    risk_factors: list[str] = []

    if confidence < 0.55:
        risk_factors.append("Analiz güveni düşük — beden seçimi belirsiz kalabilir.")

    fabric = (garment.get("fabric_cues") or "").lower()
    if "ince" in fabric:
        risk_factors.append("İnce kumaş vücut hatlarını daha belirgin gösterebilir.")
    if any(k in fabric for k in ("sert", "esnek değil", "rigid")):
        risk_factors.append("Esnek olmayan kumaş hareket konforunu etkileyebilir.")

    brand = garment.get("brand_sizing_tendency", "standart")
    if brand == "küçük kalıplı":
        risk_factors.append("Marka küçük kalıplı — bir beden büyük almayı değerlendirin.")
    elif brand == "büyük kalıplı":
        risk_factors.append("Marka büyük kalıplı — beden seçimini gözden geçirin.")

    if not state.get("body_image_ref"):
        risk_factors.append("Vücut fotoğrafı yüklenmedi — tahmin yalnızca ölçülere dayanıyor.")

    for insight in reviews[:3]:
        theme = (insight.get("theme") or "").lower()
        if any(k in theme for k in ("küçük", "dar", "büyük")):
            risk_factors.append(f"Kullanıcı yorumlarına göre: {insight['theme']}.")

    risk_score = (1.0 - confidence) * 0.50 + min(0.50, len(risk_factors) * 0.12)
    if risk_score < 0.30:
        level = "low"
    elif risk_score < 0.60:
        level = "medium"
    else:
        level = "high"

    return {
        "risk_evaluation": {
            "risk_level": level,
            "risk_level_tr": _RISK_LEVEL_LABELS[level],
            "risk_factors": risk_factors,
            "risk_score": round(risk_score, 3),
            "confidence": round(confidence, 3),
        }
    }


# ---------------------------------------------------------------------------
# Node 6: Turkish formatter (final output assembler)
# ---------------------------------------------------------------------------

def turkish_formatter_node(state: PipelineState) -> dict:
    rec  = state.get("recommendation")   or {}
    risk = state.get("risk_evaluation")  or {}
    insights = state.get("review_insights") or []

    size       = rec.get("recommended_size", "M")
    confidence = float(rec.get("confidence", 0.5))
    pct        = f"%{int(round(confidence * 100))}"

    community_tr: list[str] = []
    for ins in insights[:3]:
        theme = ins.get("theme", "")
        if theme:
            sentiment = ins.get("sentiment", "neutral")
            if sentiment == "positive":
                community_tr.append(f"Kullanıcılar olumlu değerlendiriyor: {theme}.")
            elif sentiment == "warning":
                community_tr.append(f"Dikkat: Kullanıcılar belirtiyor — {theme}.")
            else:
                community_tr.append(f"Kullanıcı yorumları: {theme}.")

    if not community_tr:
        community_tr = ["Henüz yeterli kullanıcı yorumu bulunmuyor."]

    final_response = {
        "recommended_size": size,
        "confidence_score": confidence,
        "confidence_pct": pct,
        "explanation_tr": rec.get("explanation_tr", ""),
        "risk_level": risk.get("risk_level", "medium"),
        "risk_level_tr": risk.get("risk_level_tr", "Orta Risk"),
        "risk_factors_tr": risk.get("risk_factors", []),
        "uncertainty_tr": rec.get("uncertainty_tr", ""),
        "community_insights_tr": community_tr,
    }
    return {"final_response": final_response}
