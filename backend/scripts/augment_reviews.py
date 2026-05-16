"""
Deterministic review enrichment — emits data/reviews_enriched.jsonl.

Adds four fields to each review row, derived purely from existing data:
  - returned: bool          (fits_true=False AND sentiment=negative)
  - return_reason: str|None (precedence-ordered keyword match; None when not returned)
  - fabric_breathability: str (low|medium|high — looked up from garments.json fabric)
  - season_fit: str         (summer|winter|all_season — from fabric + category)

Reasoning: the existing reviews.jsonl has no structured return reason. We
need cohort-level "%42 boy nedeniyle iade etmiş" stats for the demo, and
LLM-labelling is non-deterministic. Keyword precedence over the already-
curated `themes` field plus the review text is deterministic, auditable,
and fully reproducible.

Usage (from repo root):
    python -m backend.scripts.augment_reviews
or (from backend/):
    python -m scripts.augment_reviews

Idempotent: reads data/reviews.jsonl, writes data/reviews_enriched.jsonl.
The output is committed to git; the embedding ingest step reads from it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

# ──────────────────────────────────────────────────────────────────────
# Paths — repo root is two levels up from backend/scripts/
# ──────────────────────────────────────────────────────────────────────

_REPO_ROOT  = Path(__file__).resolve().parent.parent.parent
_DATA_DIR   = _REPO_ROOT / "data"
_REVIEWS_IN = _DATA_DIR / "reviews.jsonl"
_GARMENTS   = _DATA_DIR / "garments.json"
_REVIEWS_OUT = _DATA_DIR / "reviews_enriched.jsonl"


# ──────────────────────────────────────────────────────────────────────
# Return-reason precedence (most specific first)
# Each tuple: (reason_code, keyword tuple). First match wins.
# Match is substring over the lowercase (themes + " " + review_tr) field.
# ──────────────────────────────────────────────────────────────────────

_RETURN_REASON_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("boy_uzunluk",     ("boy ", "boyu", "etek boyu", "kısa kaldı", "kısa geldi", "bilek uzunluğu", "etek kısa", "boy uzun")),
    ("omuz",            ("omuz",)),
    ("kol",             ("kol ", "kollar", "kol uzun", "dar kol", "kolu")),
    ("kalca_bel",       ("kalça", "bel ", "beli", "gövde", "karın")),
    ("kumas",           ("kumaş", "şeffaf", "kaşın", "sert kumaş", "ince kumaş", "ucuz kumaş", "tüylen")),
    ("renk_farkli",     ("renk farklı", "fotoğraftaki", "renk uymadı", "renk başka")),
    ("kucuk_geldi",     ("küçük kal", "dar geldi", "bir beden büyük", "küçük geldi", "slim gibi")),
    ("buyuk_geldi",     ("büyük geldi", "bol geldi", "bir beden küçük", "fazla bol", "geniş geldi")),
]

_FALLBACK_REASON = "genel_uyumsuzluk"


# Fabric breathability + season rules live in app.services.fabric_rules so
# the catalog and this script can never drift. Backend path must be on
# sys.path — we run via `python -m scripts.augment_reviews` from backend/.
from app.services.fabric_rules import breathability_for, season_fit_for


# ──────────────────────────────────────────────────────────────────────
# Return reason
# ──────────────────────────────────────────────────────────────────────

def _classify_return_reason(themes: str, review_tr: str) -> str:
    """Precedence-ordered keyword match. Returns _FALLBACK_REASON if no rule fires."""
    haystack = f"{themes} {review_tr}".lower()
    for reason, kws in _RETURN_REASON_RULES:
        if any(kw in haystack for kw in kws):
            return reason
    return _FALLBACK_REASON


def _is_returned(fits_true: bool, sentiment: str) -> bool:
    """Conservative proxy: a reviewer who couldn't fit AND felt negative is
    treated as a return signal. Neutral 'didn't fit' reviewers are not — they
    typically just exchanged sizes rather than returning."""
    return (not fits_true) and sentiment.lower() == "negative"


# ──────────────────────────────────────────────────────────────────────
# Garment lookup
# ──────────────────────────────────────────────────────────────────────

def _load_garments(path: Path) -> dict[str, dict]:
    with path.open(encoding="utf-8") as f:
        items = json.load(f)
    return {it["id"]: it for it in items}


# ──────────────────────────────────────────────────────────────────────
# Enrichment
# ──────────────────────────────────────────────────────────────────────

def enrich_row(row: dict, garments: dict[str, dict]) -> dict:
    """Return a NEW dict — never mutates the input."""
    out = dict(row)

    fits_true = bool(row.get("fits_true", True))
    sentiment = str(row.get("sentiment", "neutral"))
    themes    = str(row.get("themes", ""))
    review_tr = str(row.get("review_tr", ""))

    returned = _is_returned(fits_true, sentiment)
    out["returned"] = returned
    out["return_reason"] = _classify_return_reason(themes, review_tr) if returned else None

    garment = garments.get(str(row.get("garment_id", "")), {})
    fabric   = str(garment.get("fabric", ""))
    category = str(garment.get("category", ""))
    out["fabric_breathability"] = breathability_for(fabric)
    out["season_fit"] = season_fit_for(fabric, category)

    return out


def run(reviews_in: Path = _REVIEWS_IN, garments_in: Path = _GARMENTS,
        reviews_out: Path = _REVIEWS_OUT) -> dict:
    if not reviews_in.exists():
        print(f"[ERROR] {reviews_in} not found", file=sys.stderr)
        sys.exit(1)
    if not garments_in.exists():
        print(f"[ERROR] {garments_in} not found", file=sys.stderr)
        sys.exit(1)

    garments = _load_garments(garments_in)
    print(f"[INFO] loaded {len(garments)} garments")

    rows_in: list[dict] = []
    with reviews_in.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows_in.append(json.loads(line))
    print(f"[INFO] loaded {len(rows_in)} reviews")

    enriched = [enrich_row(r, garments) for r in rows_in]

    reviews_out.parent.mkdir(parents=True, exist_ok=True)
    with reviews_out.open("w", encoding="utf-8") as f:
        for row in enriched:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Audit summary — printed for sanity, not for downstream use.
    returned_count = sum(1 for r in enriched if r["returned"])
    reason_counts: dict[str, int] = {}
    for r in enriched:
        if r["returned"]:
            reason_counts[r["return_reason"]] = reason_counts.get(r["return_reason"], 0) + 1
    print(f"[INFO] returned: {returned_count}/{len(enriched)}")
    print(f"[INFO] return_reasons: {sorted(reason_counts.items(), key=lambda kv: -kv[1])}")
    print(f"[OK] wrote {reviews_out}")

    return {
        "total": len(enriched),
        "returned": returned_count,
        "reason_counts": reason_counts,
    }


if __name__ == "__main__":
    run()
