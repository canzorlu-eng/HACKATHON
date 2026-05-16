"""
Optional Gemini narrative-rewrite pass for /api/v1/qa.

Activation:
  Settings.enable_gemini_narrative = True (env: ENABLE_GEMINI_NARRATIVE=true)

Contract:
  - Presentation-only. NEVER alters decisions, recommended sizes, or numbers.
  - Operates on the deterministic `verdict_tr` produced by the fact collectors.
  - Output is rejected (caller falls back to verdict_tr) if it contains any
    number, percentage, or count NOT present in the deterministic verdict.
  - On any failure — Gemini error, malformed response, validation reject —
    the caller silently uses the deterministic verdict. Demo never blocks.

This module is intentionally simple: a single async entry point and a small
pure validator. Tests live in tests/test_qa_narrative.py.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Number extraction & validation
# ──────────────────────────────────────────────────────────────────────

# Match: %42, %4, 42, 42.5, but also bedensubscript styles like "M","XL".
# We extract digit sequences only — sizes are letters, not numbers, and
# pass-through trivially.
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _extract_numbers(text: str) -> set[str]:
    """Returns the set of digit-only tokens in `text`, normalised.
    '42', '42.0', '42,0' all collapse to '42'. Decimal precision matters
    for our case only if Gemini invents fractional percentages, which is
    treated as a rejection anyway."""
    out: set[str] = set()
    for m in _NUMBER_RE.findall(text or ""):
        s = m.replace(",", ".")
        try:
            f = float(s)
            out.add(str(int(f)) if f.is_integer() else f"{f:.2f}")
        except ValueError:
            continue
    return out


def validate_narrative(narrative_tr: str, deterministic_verdict_tr: str,
                       facts: dict | None = None) -> bool:
    """
    Honesty rail. Reject the narrative if it introduces any number that
    isn't already in the deterministic verdict or the facts dict.

    Returns True when safe to use, False when caller must fall back.
    """
    if not narrative_tr or not narrative_tr.strip():
        return False

    allowed: set[str] = _extract_numbers(deterministic_verdict_tr)

    # Mine numbers out of every string in the facts dict too — collectors
    # may pre-format values like "%42" inside evidence_tr bullets, and that
    # counts as grounded.
    if facts:
        def _walk(v: Any) -> None:
            if isinstance(v, str):
                allowed.update(_extract_numbers(v))
            elif isinstance(v, (list, tuple)):
                for x in v:
                    _walk(x)
            elif isinstance(v, dict):
                for x in v.values():
                    _walk(x)
            elif isinstance(v, (int, float)):
                f = float(v)
                allowed.add(str(int(f)) if f.is_integer() else f"{f:.2f}")
        _walk(facts)

    proposed: set[str] = _extract_numbers(narrative_tr)
    extras = proposed - allowed
    if extras:
        logger.warning(
            "qa_narrative_rejected reason=invented_numbers extras=%s",
            sorted(extras),
        )
        return False
    return True


# ──────────────────────────────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────────────────────────────

async def maybe_compose_narrative(
    *,
    facts: dict,
    deterministic_verdict_tr: str,
    ai_client: Any,
    enabled: bool,
) -> str:
    """
    Returns the answer string to ship to the user.

    - enabled=False (default) → returns deterministic_verdict_tr unchanged.
    - enabled=True            → asks ai_client.compose_qa_narrative; if
      that returns a validated rewrite, use it; otherwise fall back to
      deterministic_verdict_tr. Errors are swallowed.
    """
    if not enabled:
        return deterministic_verdict_tr
    if not deterministic_verdict_tr:
        return deterministic_verdict_tr

    try:
        result = await ai_client.compose_qa_narrative(
            facts=facts,
            deterministic_verdict_tr=deterministic_verdict_tr,
        )
        candidate = (result or {}).get("answer_tr") or ""
    except Exception:
        logger.exception("qa_narrative_compose_failed — using deterministic")
        return deterministic_verdict_tr

    if validate_narrative(candidate, deterministic_verdict_tr, facts):
        logger.info("qa_narrative_used original_len=%d new_len=%d",
                    len(deterministic_verdict_tr), len(candidate))
        return candidate.strip()

    return deterministic_verdict_tr
