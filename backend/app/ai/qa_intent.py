"""
Deterministic Turkish keyword intent router for /api/v1/qa.

Precedence is important — more specific intents must come first. For
example "bu kalıp geniş mi?" must route to `cut_wide`, not `is_big`, even
though "geniş" overlaps. The chips on the frontend always produce the
canonical phrasing of each intent so they hit the obvious bucket; free-
text questions fall back through this same ladder.

No Gemini call. ~5ms p99. The fact collectors are where any LLM polish
might later live — but routing has to be deterministic to keep the
"WE MUST WIN" demo reproducible.
"""

from __future__ import annotations

from typing import Literal


Intent = Literal[
    "is_big",
    "fabric_sweat",
    "cut_wide",
    "similar_users",
    "return_reasons",
    "unsupported",
]


# Order matters — first match wins.
_RULES: list[tuple[Intent, tuple[str, ...]]] = [
    # Cohort intents — most specific signals
    ("return_reasons", ("iade", "geri ver", "neden iade")),
    ("similar_users",  ("benzer kullanı", "benzer alı", "başkaları", "kim ne yaşa", "ne yaşamış", "başka kullanıc")),

    # Cut/silhouette — must precede is_big because "geniş" can appear in both.
    # Use the consonant stem "kalıb"/"kalıp" because Turkish inflects p↔b
    # ("kalıbı", "kalıba", "kalıbı")
    ("cut_wide",       ("kalıp", "kalıb", "kesim", "slim mi", "oversize mi", "fit tipi", "geniş kalıp", "dar kalıp")),

    # Fabric / breathability
    ("fabric_sweat",   ("terlet", "nefes al", "hava al", "kumaş", "sıcakta", "yaz için", "yazlık mı", "yazın")),

    # Fit size feedback — broadest, must come last among the supported intents
    ("is_big",         ("büyük mü", "büyük gel", "bol gel", "bol mu", "küçük gel", "dar gel", "büyük olur", "tam beden mi")),
]


def route_intent(text: str) -> Intent:
    """Returns the first intent whose keyword set has a substring hit."""
    if not text:
        return "unsupported"
    t = text.lower().strip()
    for intent, kws in _RULES:
        if any(kw in t for kw in kws):
            return intent
    return "unsupported"
