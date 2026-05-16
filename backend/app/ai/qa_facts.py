"""
Deterministic fact collectors for the QA endpoint.

Each function takes the analysis record + user profile + (optionally) the
cohort it pulled, and produces a dict ready to template into a Turkish
answer. NO LLM CALLS — every claim traces back to:
  - the persisted Analysis.formatted_response (garment_meta, recommendation,
    risk_factors), OR
  - the catalog (fabric, breathability, season_fit), OR
  - the cohort aggregation (return_reasons, sample_quotes).

Each collector also writes a `verdict_tr` string. That string is the
fallback answer if the optional Gemini wrap is disabled or fails — and
the honesty rail uses it as the ground truth when validating Gemini
output.
"""

from __future__ import annotations

import logging
from typing import Any, Literal, Optional

from app.models.user import User
from app.services import catalog
from app.services.cohort import (
    CohortScope,
    ReturnReasonStats,
    aggregate_return_reasons,
    find_similar_reviewers,
)
from app.services.fabric_rules import BREATHABILITY_TR

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

_FIT_TYPE_TR = {
    "slim-cut": "dar",
    "slim":     "dar",
    "regular":  "normal",
    "relaxed":  "rahat",
    "oversize": "oversize",
}

_BAND_FROM_CONFIDENCE = (
    (0.70, "high"),
    (0.50, "medium"),
    (0.0,  "low"),
)


def _band_from_confidence(conf: float) -> Literal["high", "medium", "low"]:
    for threshold, band in _BAND_FROM_CONFIDENCE:
        if conf >= threshold:
            return band  # type: ignore[return-value]
    return "low"


def _fr(analysis: Any) -> dict:
    return analysis.formatted_response or {}


def _garment_meta(analysis: Any) -> dict:
    return _fr(analysis).get("garment_meta") or {}


def _representative_catalog_item(analysis: Any) -> Optional[dict]:
    """Pick a catalog row that matches the uploaded garment's category +
    brand_sizing_tendency. Used to surface fabric breathability — we don't
    have the original product in the DB, so we use the closest catalog
    archetype as a stand-in for fabric features."""
    meta = _garment_meta(analysis)
    cat = meta.get("category")
    tendency = meta.get("brand_sizing_tendency")
    if not cat:
        return None
    matches = [it for it in catalog.all_items()
               if it.get("category") == cat
               and it.get("brand_sizing_tendency") == tendency]
    if not matches:
        matches = [it for it in catalog.all_items() if it.get("category") == cat]
    return matches[0] if matches else None


# ──────────────────────────────────────────────────────────────────────
# is_big — "bu büyük mü?"
# ──────────────────────────────────────────────────────────────────────

def collect_is_big_facts(analysis: Any, user: User) -> dict:
    fr = _fr(analysis)
    meta = _garment_meta(analysis)
    rec_size = fr.get("recommended_size") or "?"
    conf = float(fr.get("confidence_score") or 0)
    tendency = meta.get("brand_sizing_tendency", "standart")
    fit_type = meta.get("fit_type", "regular")
    risk_factors = fr.get("risk_factors_tr") or []

    if tendency == "büyük kalıplı":
        lean = "big"
        verdict = (
            f"Evet, bu ürün biraz büyük kalıplı. {rec_size} beden önerilse de, "
            f"bir beden küçük almayı değerlendirebilirsiniz."
        )
    elif tendency == "küçük kalıplı":
        lean = "small"
        verdict = (
            f"Hayır, tam tersi — bu marka küçük kalıplı kesiyor. "
            f"Önerilen beden {rec_size} olsa da bir beden büyük alabilirsiniz."
        )
    elif fit_type in ("oversize", "relaxed"):
        lean = "intentionally_loose"
        verdict = (
            f"Bu ürün tasarım gereği {('oversize' if fit_type == 'oversize' else 'rahat kesimli')}. "
            f"Önerilen beden {rec_size} — bedenden büyük görünmesi normal."
        )
    else:
        lean = "standard"
        verdict = (
            f"Marka standart kalıplı görünüyor. Önerilen beden {rec_size} "
            f"sizin ölçülerinize uygun."
        )

    evidence: list[str] = []
    evidence.append(f"Önerilen beden: {rec_size}")
    evidence.append(f"Marka eğilimi: {tendency}")
    if risk_factors:
        evidence.append(risk_factors[0])

    return {
        "intent": "is_big",
        "confidence_band": _band_from_confidence(conf),
        "verdict_tr": verdict,
        "evidence_tr": evidence,
        "lean": lean,
        "recommended_size": rec_size,
        "tendency_tr": tendency,
    }


# ──────────────────────────────────────────────────────────────────────
# fabric_sweat — "kumaş terletir mi?" + "yaz için uygun mu?"
# ──────────────────────────────────────────────────────────────────────

def collect_fabric_sweat_facts(analysis: Any, user: User) -> dict:
    meta = _garment_meta(analysis)
    fabric_cues = meta.get("fabric_cues", "")
    archetype = _representative_catalog_item(analysis)

    if archetype:
        breath = archetype.get("breathability", "medium")
        fabric_name = archetype.get("fabric", fabric_cues or "Bilinmiyor")
        season = archetype.get("season_fit", "all_season")
    else:
        breath = "medium"
        fabric_name = fabric_cues or "Bilinmiyor"
        season = "all_season"

    if breath == "low":
        verdict = (
            f"Evet, bu kumaş ({fabric_name}) düşük nefes alır — sıcakta terletme "
            f"olasılığı yüksek. Yaz aylarında uzun süreli kullanım rahatsız edebilir."
        )
    elif breath == "high":
        verdict = (
            f"Hayır, bu kumaş ({fabric_name}) yüksek nefes alır — sıcakta serin "
            f"tutar, yaz kullanımına uygundur."
        )
    else:
        verdict = (
            f"Bu kumaş ({fabric_name}) orta düzeyde nefes alır — günlük kullanımda "
            f"sorun yaratmaz, ancak çok sıcak günlerde rahatsız edebilir."
        )

    evidence = [
        f"Kumaş: {fabric_name}",
        f"Nefes alabilirlik: {BREATHABILITY_TR.get(breath, breath)}",
        f"Mevsim uygunluğu: {'Yaz' if season == 'summer' else 'Kış' if season == 'winter' else 'Dört mevsim'}",
    ]

    return {
        "intent": "fabric_sweat",
        # Breathability is derived from a deterministic lookup against catalog
        # fabric — we trust it but cap at "medium" since fabric_cues comes
        # from a vision model that can mis-classify.
        "confidence_band": "medium",
        "verdict_tr": verdict,
        "evidence_tr": evidence,
        "breathability": breath,
        "season_fit": season,
        "fabric_tr": fabric_name,
    }


# ──────────────────────────────────────────────────────────────────────
# cut_wide — "bu kalıp geniş mi?"
# ──────────────────────────────────────────────────────────────────────

def collect_cut_wide_facts(analysis: Any, user: User) -> dict:
    meta = _garment_meta(analysis)
    fit_type = meta.get("fit_type", "regular")
    tendency = meta.get("brand_sizing_tendency", "standart")
    user_pref = (user.fit_preference or "regular")

    fit_tr = _FIT_TYPE_TR.get(fit_type, "normal")

    is_wide = fit_type in ("relaxed", "oversize")
    is_narrow = fit_type in ("slim-cut", "slim")

    if is_wide:
        verdict_lead = f"Evet, kalıp {fit_tr} — vücuda yapışmaz, hareket alanı geniştir."
    elif is_narrow:
        verdict_lead = f"Hayır, kalıp {fit_tr} — vücuda daha yakın oturan bir kesim."
    else:
        verdict_lead = f"Kalıp {fit_tr} — ne dar ne bol, standart bir kesim."

    # Match against user preference
    pref_match = (
        (is_wide and user_pref in ("relaxed", "oversize"))
        or (is_narrow and user_pref == "slim")
        or (fit_type == "regular" and user_pref == "regular")
    )
    match_tr = (
        "Tercihinizle uyumlu."
        if pref_match else
        f"Sizin tercihiniz ({user_pref}) ile farklı — beden seçimini gözden geçirebilirsiniz."
    )

    return {
        "intent": "cut_wide",
        "confidence_band": "high",
        "verdict_tr": f"{verdict_lead} {match_tr}",
        "evidence_tr": [
            f"Kesim: {fit_tr}",
            f"Marka eğilimi: {tendency}",
            f"Sizin tercihiniz: {user_pref}",
        ],
        "fit_type": fit_type,
        "fit_tr": fit_tr,
    }


# ──────────────────────────────────────────────────────────────────────
# similar_users + return_reasons — both consume the cohort aggregation
# ──────────────────────────────────────────────────────────────────────

def _build_cohort_evidence(
    scope: CohortScope, stats: ReturnReasonStats,
) -> list[str]:
    out: list[str] = [scope.label_tr]
    if stats.returned_pct is not None:
        out.append(f"%{stats.returned_pct}'i iade etmiş ({stats.returned_count}/{stats.total})")
    for r in stats.top_reasons[:3]:
        out.append(f"{r.reason_tr}: %{r.pct} ({r.raw_count} kişi)")
    if stats.sample_quotes_tr:
        out.append(f"Örnek yorum: \"{stats.sample_quotes_tr[0]}\"")
    return out


def _collect_cohort(analysis: Any, user: User) -> tuple[CohortScope, ReturnReasonStats]:
    meta = _garment_meta(analysis)
    category = meta.get("category", "")
    tendency = meta.get("brand_sizing_tendency", "standart")

    rows, scope = find_similar_reviewers(
        category=category,
        brand_sizing_tendency=tendency,
        height_cm=int(user.height_cm or 170),
        weight_kg=int(user.weight_kg or 65),
    )
    stats = aggregate_return_reasons(rows)
    return scope, stats


def collect_similar_users_facts(analysis: Any, user: User) -> dict:
    scope, stats = _collect_cohort(analysis, user)

    if stats.confidence_band == "low":
        return {
            "intent": "similar_users",
            "confidence_band": "low",
            "verdict_tr": (
                "Sizin ölçülerinize ve bu kategoriye yakın yeterli sayıda "
                "kullanıcı yorumu bulamadık — paylaşılabilir bir örüntü yok."
            ),
            "evidence_tr": [scope.label_tr],
            "cohort_scope_tr": scope.label_tr,
        }

    fit_pct = 100 - (stats.returned_pct or 0)
    top = stats.top_reasons[0] if stats.top_reasons else None

    if top:
        verdict = (
            f"{scope.label_tr}: %{fit_pct}'i memnun kalmış, %{stats.returned_pct}'i "
            f"iade etmiş. Önemli geri bildirim: {top.reason_tr.lower()}."
        )
    else:
        verdict = (
            f"{scope.label_tr}: %{fit_pct}'i memnun kalmış. "
            f"İade eden çıkmamış."
        )

    return {
        "intent": "similar_users",
        "confidence_band": stats.confidence_band,
        "verdict_tr": verdict,
        "evidence_tr": _build_cohort_evidence(scope, stats),
        "cohort_scope_tr": scope.label_tr,
    }


def collect_return_reasons_facts(analysis: Any, user: User) -> dict:
    scope, stats = _collect_cohort(analysis, user)

    if stats.confidence_band == "low":
        return {
            "intent": "return_reasons",
            "confidence_band": "low",
            "verdict_tr": (
                "Bu ürünle eşleşen yeterli iade verisi bulamadık — "
                "güvenilir bir iade nedeni paylaşamayız."
            ),
            "evidence_tr": [scope.label_tr],
            "cohort_scope_tr": scope.label_tr,
        }

    if stats.returned_count == 0:
        return {
            "intent": "return_reasons",
            "confidence_band": stats.confidence_band,
            "verdict_tr": (
                f"{scope.label_tr} arasında iade eden çıkmamış — "
                f"bu kategoride iade sinyali zayıf."
            ),
            "evidence_tr": [scope.label_tr, "İade oranı: %0"],
            "cohort_scope_tr": scope.label_tr,
        }

    top = stats.top_reasons[0]
    rest = stats.top_reasons[1:3]
    verdict = (
        f"Benzer kullanıcıların %{stats.returned_pct}'i iade etmiş "
        f"({stats.returned_count}/{stats.total}). En sık neden: "
        f"{top.reason_tr.lower()} (%{top.pct})."
    )
    if rest:
        secondary = "; ".join(f"{r.reason_tr.lower()} %{r.pct}" for r in rest)
        verdict += f" Diğer nedenler: {secondary}."

    return {
        "intent": "return_reasons",
        "confidence_band": stats.confidence_band,
        "verdict_tr": verdict,
        "evidence_tr": _build_cohort_evidence(scope, stats),
        "cohort_scope_tr": scope.label_tr,
    }


# ──────────────────────────────────────────────────────────────────────
# unsupported fallback
# ──────────────────────────────────────────────────────────────────────

_UNSUPPORTED_TR = (
    "Bu soruya yanıt veremem — HIWALOY yalnızca beden, kalıp, kumaş, "
    "benzer kullanıcı deneyimi ve iade nedenleri üzerine yanıt verir. "
    "Aşağıdaki önerilen sorulardan birini deneyebilirsiniz."
)


def collect_unsupported_facts(analysis: Any, user: User) -> dict:
    return {
        "intent": "unsupported",
        "confidence_band": "low",
        "verdict_tr": _UNSUPPORTED_TR,
        "evidence_tr": [],
    }


# ──────────────────────────────────────────────────────────────────────
# Dispatch
# ──────────────────────────────────────────────────────────────────────

_DISPATCH = {
    "is_big":          collect_is_big_facts,
    "fabric_sweat":    collect_fabric_sweat_facts,
    "cut_wide":        collect_cut_wide_facts,
    "similar_users":   collect_similar_users_facts,
    "return_reasons":  collect_return_reasons_facts,
    "unsupported":     collect_unsupported_facts,
}


def collect_facts_for(intent: str, analysis: Any, user: User) -> dict:
    fn = _DISPATCH.get(intent, collect_unsupported_facts)
    return fn(analysis, user)
