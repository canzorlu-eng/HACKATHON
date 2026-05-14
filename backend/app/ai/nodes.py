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
    {"theme": "beden tablosunu kontrol edin", "sentiment": "neutral", "is_fallback": True},
    {"theme": "kumaş kalitesi iyi", "sentiment": "positive", "is_fallback": True},
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
                stats_dict = result.stats.model_dump() if result.stats else None
                return {
                    "review_insights": result.as_pipeline_dicts,
                    "review_retrieval_status": result.status,
                    "review_stats": stats_dict,
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
        insights.insert(0, {"theme": "bir beden büyük alınmasını öneriyor", "sentiment": "warning", "is_fallback": True})
    elif brand == "büyük kalıplı":
        insights.insert(0, {"theme": "bir beden küçük alınmasını öneriyor", "sentiment": "warning", "is_fallback": True})

    logger.info(
        "review_retriever source=fallback insights=%d category=%s",
        len(insights), category,
    )
    return {
        "review_insights": insights,
        "review_retrieval_status": "fallback",
        "review_stats": None,
    }


# ---------------------------------------------------------------------------
# Node 4: Recommendation generator (deterministic)
# ---------------------------------------------------------------------------

def recommendation_generator_node(state: PipelineState) -> dict:
    body    = state.get("body_analysis")    or {}
    garment = state.get("garment_analysis") or {}

    # Gate: if the garment analyzer reports the image isn't a garment, bail out
    # honestly instead of fabricating a size + risk + insights.
    if garment.get("is_garment") is False:
        logger.info("recommendation skipped — image is not a garment")
        return {
            "recommendation": {
                "recommended_size": None,
                "confidence": 0.0,
                "explanation_tr": (
                    "Yüklenen görselde tanınabilir bir kıyafet bulunamadı. "
                    "Lütfen kıyafet fotoğrafı yükleyin."
                ),
                "uncertainty_tr": garment.get(
                    "uncertainty_reason", "Görsel bir kıyafet içermiyor."
                ),
                "garment_invalid": True,
            }
        }

    height_cm   = state.get("height_cm", 170)
    weight_kg   = state.get("weight_kg", 65)
    user_pref   = state.get("fit_preference", "regular")
    has_body_img = bool(state.get("body_image_ref"))

    bmi = weight_kg / ((height_cm / 100) ** 2)
    base_size = _size_from_bmi(bmi, height_cm)

    fit_tendency = body.get("fit_tendency", "standart")
    fit_type     = garment.get("fit_type", "regular")
    brand        = garment.get("brand_sizing_tendency", "standart")

    # Map Gemini's English fit_type tokens to Turkish adjective form.
    _FIT_TYPE_TR = {
        "slim-cut": "dar",
        "slim":     "dar",
        "regular":  "normal",
        "relaxed":  "rahat",
        "oversize": "oversize",
    }
    fit_type_tr = _FIT_TYPE_TR.get(fit_type, "normal")

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
        f"Beden ölçüleriniz ve kıyafetin {fit_type_tr} kesimine göre "
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

    # Garment-invalid path: no risk to evaluate.
    if rec.get("garment_invalid"):
        return {
            "risk_evaluation": {
                "risk_level": None,
                "risk_level_tr": None,
                "risk_factors": [],
                "risk_score": 0.0,
                "confidence": 0.0,
            }
        }

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

_REGION_LOW    = "low"
_REGION_MEDIUM = "medium"
_REGION_HIGH   = "high"


def _compute_risk_heatmap(
    body: dict,
    garment: dict,
    has_body_image: bool,
    height_cm: int,
    weight_kg: int,
) -> list[dict]:
    """Derive per-body-region risk status from upstream analysis data.

    Returns a list of {"region", "label_tr", "status", "reason_tr"} dicts.
    Without a body image, body-shape-dependent regions are capped at
    "medium" — we don't claim "high" on data we don't have.
    """
    fit_type      = garment.get("fit_type", "regular")
    shoulder_est  = body.get("shoulder_width_estimate", "standart")
    fabric        = (garment.get("fabric_cues") or "").lower()
    brand         = garment.get("brand_sizing_tendency", "standart")

    try:
        bmi = weight_kg / ((height_cm / 100) ** 2) if height_cm else 22.0
    except ZeroDivisionError:
        bmi = 22.0

    def cap(status: str) -> str:
        if not has_body_image and status == _REGION_HIGH:
            return _REGION_MEDIUM
        return status

    regions: list[dict] = []

    # ── Omuz ─────────────────────────────────────────────
    if fit_type == "slim-cut" and shoulder_est == "geniş":
        regions.append({
            "region": "omuz",
            "label_tr": "Omuz",
            "status": cap(_REGION_HIGH),
            "reason_tr": "Dar kesim ve geniş omuz tahmini birleşince omuz alanı sıkışabilir.",
        })
    elif fit_type == "slim-cut":
        regions.append({
            "region": "omuz",
            "label_tr": "Omuz",
            "status": _REGION_MEDIUM,
            "reason_tr": "Slim-cut kesim — omuz hareket alanı sınırlı olabilir.",
        })
    elif brand == "küçük kalıplı":
        regions.append({
            "region": "omuz",
            "label_tr": "Omuz",
            "status": _REGION_MEDIUM,
            "reason_tr": "Marka küçük kalıplı — omuzlarda darlık olabilir.",
        })
    else:
        regions.append({
            "region": "omuz",
            "label_tr": "Omuz",
            "status": _REGION_LOW,
            "reason_tr": "Omuz alanında belirgin bir risk yok.",
        })

    # ── Kol ──────────────────────────────────────────────
    if brand == "küçük kalıplı" and fit_type in ("slim-cut", "regular"):
        regions.append({
            "region": "kol",
            "label_tr": "Kol",
            "status": cap(_REGION_HIGH),
            "reason_tr": "Küçük kalıplı marka + dar kollu kesim — kol darlığı riski.",
        })
    elif fit_type == "slim-cut":
        regions.append({
            "region": "kol",
            "label_tr": "Kol",
            "status": _REGION_MEDIUM,
            "reason_tr": "Slim-cut kollar hareket konforunu sınırlayabilir.",
        })
    elif fit_type in ("relaxed", "oversize"):
        regions.append({
            "region": "kol",
            "label_tr": "Kol",
            "status": _REGION_LOW,
            "reason_tr": "Rahat kesim kollar — hareket konforu yüksek.",
        })
    else:
        regions.append({
            "region": "kol",
            "label_tr": "Kol",
            "status": _REGION_LOW,
            "reason_tr": "Kol kesimi profile uyumlu.",
        })

    # ── Bel ──────────────────────────────────────────────
    thin_fabric = any(k in fabric for k in ("ince", "kaygan", "saten"))
    if thin_fabric and bmi > 25:
        regions.append({
            "region": "bel",
            "label_tr": "Bel",
            "status": cap(_REGION_HIGH),
            "reason_tr": "İnce kumaş + yüksek BMI — bel hattı daha belirgin görünebilir.",
        })
    elif fit_type == "slim-cut" and bmi > 24:
        regions.append({
            "region": "bel",
            "label_tr": "Bel",
            "status": _REGION_MEDIUM,
            "reason_tr": "Slim-cut + BMI birleşimi — bel rahatlığı düşebilir.",
        })
    elif fit_type in ("relaxed", "oversize"):
        regions.append({
            "region": "bel",
            "label_tr": "Bel",
            "status": _REGION_LOW,
            "reason_tr": "Bol kesim bel hattına basınç yapmaz.",
        })
    else:
        regions.append({
            "region": "bel",
            "label_tr": "Bel",
            "status": _REGION_LOW,
            "reason_tr": "Bel alanında belirgin bir risk yok.",
        })

    return regions


def turkish_formatter_node(state: PipelineState) -> dict:
    rec  = state.get("recommendation")   or {}
    risk = state.get("risk_evaluation")  or {}
    insights = state.get("review_insights") or []

    # Garment-invalid path: short, honest response — no fabricated fields.
    if rec.get("garment_invalid"):
        return {
            "final_response": {
                "recommended_size": None,
                "confidence_score": None,
                "confidence_pct": None,
                "explanation_tr": rec.get("explanation_tr", ""),
                "risk_level": None,
                "risk_level_tr": None,
                "risk_factors_tr": [],
                "uncertainty_tr": rec.get("uncertainty_tr", ""),
                "community_insights_tr": [],
            }
        }

    size       = rec.get("recommended_size", "M")
    confidence = float(rec.get("confidence", 0.5))
    pct        = f"%{int(round(confidence * 100))}"

    community_tr: list[str] = []
    for ins in insights[:3]:
        # Grounded service insights use `theme_tr`; fallback insights use `theme`.
        theme = ins.get("theme_tr") or ins.get("theme", "")
        if not theme:
            continue
        if ins.get("is_fallback"):
            sentiment = ins.get("sentiment", "neutral")
            if sentiment == "warning":
                community_tr.append(f"Genel öneri: {theme}.")
            else:
                community_tr.append(f"Genel bilgi: {theme}.")
        else:
            sentiment = ins.get("sentiment", "neutral")
            if sentiment == "positive":
                community_tr.append(f"Kullanıcılar olumlu değerlendiriyor: {theme}.")
            elif sentiment == "warning":
                community_tr.append(f"Dikkat: Kullanıcılar belirtiyor — {theme}.")
            else:
                community_tr.append(f"Kullanıcı yorumları: {theme}.")

    if not community_tr:
        community_tr = ["Henüz yeterli kullanıcı yorumu bulunmuyor."]

    heatmap = _compute_risk_heatmap(
        body=state.get("body_analysis") or {},
        garment=state.get("garment_analysis") or {},
        has_body_image=bool(state.get("body_image_ref")),
        height_cm=int(state.get("height_cm") or 170),
        weight_kg=int(state.get("weight_kg") or 65),
    )

    final_response = {
        "recommended_size": size,
        "confidence_score": confidence,
        "confidence_pct": pct,
        "explanation_tr": rec.get("explanation_tr", ""),
        "detailed_explanation_tr": state.get("detailed_explanation_tr") or None,
        "risk_level": risk.get("risk_level", "medium"),
        "risk_level_tr": risk.get("risk_level_tr", "Orta Risk"),
        "risk_factors_tr": risk.get("risk_factors", []),
        "uncertainty_tr": rec.get("uncertainty_tr", ""),
        "community_insights_tr": community_tr,
        "risk_heatmap": heatmap,
    }
    return {"final_response": final_response}


# ---------------------------------------------------------------------------
# Node 5b: Narrative composer — Gemini-written detailed explanation
# Runs after risk_evaluator so it can quote the final confidence/risk too.
# ---------------------------------------------------------------------------

def make_narrative_composer_node(ai_client):
    """Returns a LangGraph-compatible async node bound to the given ai_client."""

    async def narrative_composer_node(state: PipelineState) -> dict:
        rec = state.get("recommendation") or {}
        # No detailed narrative when the garment gate already short-circuited.
        if rec.get("garment_invalid"):
            return {"detailed_explanation_tr": None}

        body    = dict(state.get("body_analysis") or {})
        garment = state.get("garment_analysis") or {}
        risk    = state.get("risk_evaluation")  or {}
        stats   = state.get("review_stats")     or {}
        has_body_image = bool(state.get("body_image_ref"))
        profile = {
            "height_cm":      state.get("height_cm"),
            "weight_kg":      state.get("weight_kg"),
            "fit_preference": state.get("fit_preference"),
            "has_body_image": has_body_image,
        }

        # Without a body image, the analyzer's shoulder/torso/silhouette
        # estimates are placeholder defaults — not observations. Strip them
        # so Gemini cannot fabricate "Geniş omuz yapınız" from a default.
        if not has_body_image:
            for k in (
                "shoulder_width_estimate",
                "torso_length_estimate",
                "proportional_notes",
                "silhouette_type",
            ):
                body.pop(k, None)

        try:
            result = await ai_client.compose_narrative(
                profile=profile,
                body_analysis=body,
                garment_analysis=garment,
                recommendation=rec,
                risk_evaluation=risk,
                review_stats=stats,
            )
            text = (result or {}).get("detailed_explanation_tr")
            if text:
                logger.info("narrative_composed length=%d", len(text))
                return {"detailed_explanation_tr": text}
        except Exception:
            logger.exception("narrative_composer_failed")

        return {"detailed_explanation_tr": None}

    return narrative_composer_node
