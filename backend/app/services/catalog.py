"""
Local garment catalog service.

Loads data/garments.json once at import time and augments each row with a
derived `price_tl` (the dataset ships without prices for MVP). Provides
filtering helpers used by the /stylist endpoint to build a small shortlist
that Gemini reasons over — Gemini never sees the raw filename and cannot
invent products outside this list.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

from app.services.fabric_rules import breathability_for, season_fit_for

logger = logging.getLogger(__name__)

# data/garments.json sits at the repo root in dev, or copied to /app/data in
# the backend container. We look in both.
_CANDIDATE_PATHS = [
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "garments.json",  # repo root
    Path("/app/data/garments.json"),
    Path(__file__).resolve().parent.parent.parent / "data" / "garments.json",          # backend/data
]


# Rough Turkish-market base prices (TL) per category for an MVP mock.
_BASE_PRICE_TL = {
    "tshirt": 350,
    "shirt":  600,
    "jeans":  800,
    "dress":  700,
    "jacket": 1500,
}

# Brand tier multipliers — fully cosmetic, only here so the price field has
# some signal for budget filtering in the demo.
_BRAND_TIER = {
    # Premium
    "Massimo Dutti": 1.4, "Calvin Klein": 1.4, "Tommy Hilfiger": 1.4,
    "Levi's": 1.4, "Nike": 1.4, "Adidas": 1.4,
    # Mid-premium
    "Zara": 1.1, "Mango": 1.1,
    # Mid
    "Mavi": 1.0, "Pull&Bear": 1.0, "Bershka": 1.0, "Stradivarius": 1.0,
    # Budget
    "LC Waikiki": 0.7, "Koton": 0.7, "H&M": 0.7, "DeFacto": 0.7,
}


def _derive_price_tl(item: dict) -> int:
    base = _BASE_PRICE_TL.get(item.get("category"), 500)
    tier = _BRAND_TIER.get(item.get("brand"), 1.0)
    return int(round(base * tier / 10.0) * 10)


def _load() -> list[dict]:
    for path in _CANDIDATE_PATHS:
        if path.exists():
            logger.info("loading garment catalog from %s", path)
            with path.open(encoding="utf-8") as f:
                items = json.load(f)
            for it in items:
                it["price_tl"] = _derive_price_tl(it)
                it["breathability"] = breathability_for(it.get("fabric", ""))
                it["season_fit"]    = season_fit_for(
                    it.get("fabric", ""), it.get("category", "")
                )
            return items
    logger.warning("garments.json not found in any candidate path")
    return []


_CATALOG: list[dict] = _load()


# Public API ------------------------------------------------------------------

def all_items() -> list[dict]:
    return list(_CATALOG)


def get_by_id(garment_id: str) -> Optional[dict]:
    for it in _CATALOG:
        if it["id"] == garment_id:
            return it
    return None


# Query parsing ---------------------------------------------------------------

# "500 TL altı/altında", "500 lira", "300 tl civarı", "ucuz", "uygun fiyatlı"
_PRICE_PATTERNS = [
    re.compile(r"(\d{2,5})\s*(?:tl|lira|₺)", re.IGNORECASE),
]
_BUDGET_KEYWORDS_LOW = ("ucuz", "uygun fiyat", "bütçe dostu", "düşük bütçe")


def extract_max_price_tl(query: str, explicit_max: Optional[int] = None) -> Optional[int]:
    """Find a price ceiling expressed in the query, or use the explicit override."""
    if explicit_max is not None and explicit_max > 0:
        return int(explicit_max)
    for pat in _PRICE_PATTERNS:
        m = pat.search(query)
        if m:
            return int(m.group(1))
    if any(kw in query.lower() for kw in _BUDGET_KEYWORDS_LOW):
        return 400  # rough "budget-friendly" ceiling
    return None


# Category keyword hints — only used as a soft pre-filter when the query
# clearly names one. The LLM still does the final selection.
_CATEGORY_HINTS = {
    "shirt":  ("gömlek",),
    "tshirt": ("tişört", "t-shirt", "tshirt", "kazak", "sweatshirt", "hoodie", "triko"),
    "jeans":  ("jean", "pantolon", "chino", "kot"),
    "dress":  ("elbise",),
    "jacket": ("ceket", "mont", "blazer", "rüzgarlık", "bomber"),
}


def detect_categories(query: str) -> list[str]:
    q = query.lower()
    hits = [cat for cat, words in _CATEGORY_HINTS.items() if any(w in q for w in words)]
    return hits


# Filtering -------------------------------------------------------------------

def filter_shortlist(
    *,
    query: str,
    max_price_tl: Optional[int] = None,
    user_fit_preference: Optional[str] = None,
    limit: int = 12,
) -> list[dict]:
    """
    Build a shortlist Gemini can reason over (≤ limit items).

    Hard filters:
      - price ≤ max_price_tl (if given)
      - category in detected categories (if any were named)
    Soft signal:
      - user_fit_preference promotes matching fit_type items to the top so a
        shortlist of 12 is more likely to contain compatible options.
    """
    items = all_items()

    if max_price_tl is not None:
        items = [it for it in items if it["price_tl"] <= max_price_tl]

    cats = detect_categories(query)
    if cats:
        items = [it for it in items if it["category"] in cats]

    if user_fit_preference:
        # Sort matches first, then everything else (stable).
        pref_match = "slim-cut" if user_fit_preference == "slim" else user_fit_preference
        items.sort(key=lambda it: 0 if it.get("fit_type") == pref_match else 1)

    return items[:limit]
