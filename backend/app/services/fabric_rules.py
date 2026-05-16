"""Single source of truth for fabric breathability + seasonality rules.

Used by:
  - app.services.catalog (annotates each garment at load time)
  - scripts.augment_reviews (annotates each review based on its garment)

Keep these two consumers in lockstep — otherwise the fabric_sweat QA intent
would compare apples (cohort breathability) to oranges (catalog breathability).
"""

from __future__ import annotations


_HIGH_BREATH = ("keten", "muslin", "viskon", "şifon")
_LOW_BREATH  = ("saten", "polar", "yün", "tüy", "naylon", "polyester dolgu", "deri")

_WINTER_KEYS = ("kalın", "sıcak", "tüy dolgu", "polar", "yün", "puffer", "rüzgarlık", "mont")
_SUMMER_KEYS = ("yaz", "yazlık", "ince", "serin", "keten", "muslin")


def breathability_for(fabric: str) -> str:
    """Returns 'high', 'medium', or 'low'. Substring match against fabric."""
    f = (fabric or "").lower()
    if any(k in f for k in _HIGH_BREATH):
        return "high"
    if any(k in f for k in _LOW_BREATH):
        return "low"
    return "medium"


def season_fit_for(fabric: str, category: str) -> str:
    """Returns 'summer', 'winter', or 'all_season'."""
    f = (fabric or "").lower()
    c = (category or "").lower()
    if any(k in f for k in _WINTER_KEYS) or c == "jacket":
        return "winter"
    if any(k in f for k in _SUMMER_KEYS):
        return "summer"
    return "all_season"


BREATHABILITY_TR: dict[str, str] = {
    "high":   "Yüksek nefes alır",
    "medium": "Orta nefes alır",
    "low":    "Düşük nefes alır",
}

SEASON_TR: dict[str, str] = {
    "summer":     "Yaz",
    "winter":     "Kış",
    "all_season": "Dört mevsim",
}
