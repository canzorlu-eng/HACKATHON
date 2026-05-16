"""
Cohort service — powers the "%X benzer kullanıcı şu nedenle iade etmiş" panel
and the similar_users / return_reasons QA intents.

Loads data/reviews_enriched.jsonl once at import. Pure-Python aggregation —
no Chroma, no LLM. The enrichment script (backend/scripts/augment_reviews.py)
guarantees every row carries `returned` and `return_reason` fields.

Two-stage cohort relaxation:
    Stage A: same category + brand_sizing_tendency, height±5cm, weight±7kg
    Stage B: same category only
The chosen stage is surfaced in `scope_tr` so the UI never lies about how
broad the cohort is.

Confidence bands suppress headline percentages on tiny samples — we never
publish a percentage backed by <5 reviewers.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Data loading
# ──────────────────────────────────────────────────────────────────────

_CANDIDATE_REVIEWS = [
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "reviews_enriched.jsonl",
    Path("/app/data/reviews_enriched.jsonl"),
    Path(__file__).resolve().parent.parent.parent / "data" / "reviews_enriched.jsonl",
]
_CANDIDATE_GARMENTS = [
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "garments.json",
    Path("/app/data/garments.json"),
    Path(__file__).resolve().parent.parent.parent / "data" / "garments.json",
]


def _load_reviews() -> list[dict]:
    for path in _CANDIDATE_REVIEWS:
        if path.exists():
            rows: list[dict] = []
            with path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        rows.append(json.loads(line))
            logger.info("cohort: loaded %d enriched reviews from %s", len(rows), path)
            return rows
    logger.warning("cohort: reviews_enriched.jsonl not found in any candidate path")
    return []


def _load_garment_index() -> dict[str, dict]:
    for path in _CANDIDATE_GARMENTS:
        if path.exists():
            with path.open(encoding="utf-8") as f:
                items = json.load(f)
            return {it["id"]: it for it in items}
    logger.warning("cohort: garments.json not found")
    return {}


_REVIEWS: list[dict] = _load_reviews()
_GARMENT_INDEX: dict[str, dict] = _load_garment_index()

# Join reviews with garment metadata so cohort filters can use category/brand_sizing_tendency.
for _r in _REVIEWS:
    _gid = str(_r.get("garment_id", ""))
    _g = _GARMENT_INDEX.get(_gid, {})
    _r["_category"] = _g.get("category", "")
    _r["_brand_sizing_tendency"] = _g.get("brand_sizing_tendency", "")


# ──────────────────────────────────────────────────────────────────────
# Public types
# ──────────────────────────────────────────────────────────────────────

# Stage A relaxation bounds. Tuned for ~160 reviews × 50 garments.
_HEIGHT_TOL_CM = 5
_WEIGHT_TOL_KG = 7

# Confidence band thresholds — see plan §"Critical design rules".
_BAND_HIGH = 15
_BAND_MED  = 5


REASON_TR: dict[str, str] = {
    "boy_uzunluk":      "Boy / uzunluk",
    "omuz":             "Omuz darlığı",
    "kol":              "Kol kesimi",
    "kalca_bel":        "Kalça / bel",
    "kumas":            "Kumaş kalitesi",
    "renk_farkli":      "Renk farkı",
    "kucuk_geldi":      "Beden küçük geldi",
    "buyuk_geldi":      "Beden büyük geldi",
    "genel_uyumsuzluk": "Genel uyumsuzluk",
}


@dataclass
class CohortScope:
    stage: Literal["A", "B", "none"]
    total: int
    label_tr: str


@dataclass
class ReasonStat:
    reason: str
    reason_tr: str
    raw_count: int
    pct: int               # share of RETURNED cohort, not the full cohort


@dataclass
class ReturnReasonStats:
    total: int
    returned_count: int
    returned_pct: Optional[int]                   # None when confidence_band == "low"
    confidence_band: Literal["high", "medium", "low"]
    top_reasons: list[ReasonStat] = field(default_factory=list)
    sample_quotes_tr: list[str] = field(default_factory=list)
    fabric_breathability_breakdown: dict[str, int] = field(default_factory=dict)


# ──────────────────────────────────────────────────────────────────────
# Cohort search — two-stage relaxation
# ──────────────────────────────────────────────────────────────────────

def find_similar_reviewers(
    *,
    category: str,
    brand_sizing_tendency: str,
    height_cm: int,
    weight_kg: int,
) -> tuple[list[dict], CohortScope]:
    """
    Returns (cohort_rows, scope). cohort_rows is a slice of _REVIEWS that
    match the requested filter. scope.label_tr is human-readable for the
    UI badge.
    """
    if not _REVIEWS:
        return [], CohortScope(stage="none", total=0,
                               label_tr="Yeterli benzer kullanıcı verisi yok")

    # Stage A: category + brand_sizing_tendency + body envelope
    stage_a = [
        r for r in _REVIEWS
        if r["_category"] == category
        and r["_brand_sizing_tendency"] == brand_sizing_tendency
        and abs(int(r.get("height_cm", 0)) - height_cm) <= _HEIGHT_TOL_CM
        and abs(int(r.get("weight_kg", 0)) - weight_kg) <= _WEIGHT_TOL_KG
    ]
    if len(stage_a) >= _BAND_MED:
        label = (
            f"Benzer {len(stage_a)} alıcı "
            f"(aynı kategori, ±{_HEIGHT_TOL_CM} cm boy, ±{_WEIGHT_TOL_KG} kg)"
        )
        return stage_a, CohortScope(stage="A", total=len(stage_a), label_tr=label)

    # Stage B: same category only
    stage_b = [r for r in _REVIEWS if r["_category"] == category]
    if stage_b:
        label = f"{len(stage_b)} alıcı (aynı kategori)"
        return stage_b, CohortScope(stage="B", total=len(stage_b), label_tr=label)

    return [], CohortScope(stage="none", total=0,
                           label_tr="Yeterli benzer kullanıcı verisi yok")


# ──────────────────────────────────────────────────────────────────────
# Aggregation
# ──────────────────────────────────────────────────────────────────────

def _confidence_band(n: int) -> Literal["high", "medium", "low"]:
    if n >= _BAND_HIGH:
        return "high"
    if n >= _BAND_MED:
        return "medium"
    return "low"


def aggregate_return_reasons(
    cohort: list[dict],
    *,
    max_quotes: int = 3,
    max_reasons: int = 3,
) -> ReturnReasonStats:
    """Counts. All numbers are real, derived from the cohort metadata."""
    total = len(cohort)
    band = _confidence_band(total)

    if total == 0:
        return ReturnReasonStats(
            total=0, returned_count=0, returned_pct=None,
            confidence_band="low",
        )

    returned_rows = [r for r in cohort if r.get("returned") is True]
    returned_count = len(returned_rows)

    reason_counts: dict[str, int] = {}
    for r in returned_rows:
        rs = r.get("return_reason") or "genel_uyumsuzluk"
        reason_counts[rs] = reason_counts.get(rs, 0) + 1

    top_reasons: list[ReasonStat] = []
    if returned_count > 0:
        for reason, count in sorted(reason_counts.items(),
                                    key=lambda kv: kv[1], reverse=True)[:max_reasons]:
            pct = int(round(count / returned_count * 100))
            top_reasons.append(ReasonStat(
                reason=reason,
                reason_tr=REASON_TR.get(reason, reason),
                raw_count=count,
                pct=pct,
            ))

    # Verbatim quotes from returned reviewers — never invented, always
    # the original review_tr field. Cap at max_quotes.
    quotes: list[str] = []
    for r in returned_rows[:max_quotes]:
        text = str(r.get("review_tr", "")).strip()
        if text:
            quotes.append(text)

    # Fabric breathability breakdown (used by fabric_sweat intent).
    breath_breakdown: dict[str, int] = {}
    for r in cohort:
        b = str(r.get("fabric_breathability", "medium"))
        breath_breakdown[b] = breath_breakdown.get(b, 0) + 1

    returned_pct: Optional[int]
    if band == "low":
        # Suppress headline percentages on tiny samples per the honesty rail.
        returned_pct = None
        top_reasons = []
    else:
        returned_pct = int(round(returned_count / total * 100))

    return ReturnReasonStats(
        total=total,
        returned_count=returned_count,
        returned_pct=returned_pct,
        confidence_band=band,
        top_reasons=top_reasons,
        sample_quotes_tr=quotes,
        fabric_breathability_breakdown=breath_breakdown,
    )


# ──────────────────────────────────────────────────────────────────────
# Test-only reset hook
# ──────────────────────────────────────────────────────────────────────

def _replace_reviews_for_test(rows: list[dict]) -> None:
    """Used by unit tests to inject a fixture cohort without touching disk."""
    global _REVIEWS
    _REVIEWS = [dict(r) for r in rows]
    for r in _REVIEWS:
        if "_category" not in r:
            gid = str(r.get("garment_id", ""))
            g = _GARMENT_INDEX.get(gid, {})
            r["_category"] = g.get("category", r.get("_category", ""))
            r["_brand_sizing_tendency"] = g.get("brand_sizing_tendency", r.get("_brand_sizing_tendency", ""))
