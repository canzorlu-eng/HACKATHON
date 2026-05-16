"""Tests for the optional Gemini narrative-rewrite pass and its honesty rail."""

import asyncio
import pytest

from app.ai.qa_narrative import (
    _extract_numbers,
    maybe_compose_narrative,
    validate_narrative,
)


# ---------------------------------------------------------------------------
# Pure validator
# ---------------------------------------------------------------------------

def test_extract_numbers_handles_percent_and_decimals():
    s = "Benzer 18 alıcının %42'si iade etmiş, 1.5 yıllık veri."
    out = _extract_numbers(s)
    assert {"18", "42"}.issubset(out)
    assert "1.50" in out


def test_validate_accepts_narrative_that_only_repeats_existing_numbers():
    verdict = "Önerilen beden M. Benzer 12 alıcının %25'i iade etmiş."
    narrative = (
        "Önerilen beden M olarak görünüyor. Benzer 12 alıcının %25'i bu ürünü iade etmiş."
    )
    assert validate_narrative(narrative, verdict) is True


def test_validate_rejects_invented_percentage():
    verdict = "Benzer 12 alıcının %25'i iade etmiş."
    narrative = "Benzer 12 alıcının %25'i iade etmiş, %42'si memnun."   # %42 not in verdict
    assert validate_narrative(narrative, verdict) is False


def test_validate_rejects_invented_count():
    verdict = "Önerilen beden M, marka standart kalıplı."
    narrative = "Önerilen beden M, 80 kullanıcı bu marka standart kalıplı."  # 80 invented
    assert validate_narrative(narrative, verdict) is False


def test_validate_accepts_numbers_present_in_facts_evidence():
    # Sometimes the verdict has no number, but evidence_tr does — that's fine.
    verdict = "Marka küçük kalıplı — bir beden büyük alabilirsiniz."
    facts = {
        "evidence_tr": ["Benzer 18 alıcı (aynı kategori, ±5 cm boy)"],
    }
    narrative = "Marka küçük kalıplı. Benzer 18 alıcının yorumlarına göre büyük alın."
    assert validate_narrative(narrative, verdict, facts) is True


def test_validate_rejects_empty_narrative():
    assert validate_narrative("", "Önerilen beden M.") is False
    assert validate_narrative("   ", "Önerilen beden M.") is False


# ---------------------------------------------------------------------------
# maybe_compose_narrative — feature flag behavior
# ---------------------------------------------------------------------------

class _StubClient:
    def __init__(self, payload: dict | None = None, raise_exc: bool = False):
        self.payload = payload or {}
        self.raise_exc = raise_exc
        self.calls = 0

    async def compose_qa_narrative(self, facts, deterministic_verdict_tr):
        self.calls += 1
        if self.raise_exc:
            raise RuntimeError("simulated Gemini failure")
        return self.payload


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_flag_off_returns_deterministic_unchanged_and_skips_client():
    client = _StubClient(payload={"answer_tr": "should not be used"})
    out = _run(maybe_compose_narrative(
        facts={"intent": "is_big"},
        deterministic_verdict_tr="Önerilen beden M.",
        ai_client=client,
        enabled=False,
    ))
    assert out == "Önerilen beden M."
    assert client.calls == 0


def test_flag_on_valid_rewrite_is_used():
    verdict = "Marka küçük kalıplı — bir beden büyük alabilirsiniz."
    client = _StubClient(payload={"answer_tr": (
        "Marka küçük kalıplı görünüyor; bir beden büyük almanız önerilir."
    )})
    out = _run(maybe_compose_narrative(
        facts={"verdict_tr": verdict, "evidence_tr": []},
        deterministic_verdict_tr=verdict,
        ai_client=client,
        enabled=True,
    ))
    assert "Marka küçük kalıplı" in out
    assert client.calls == 1


def test_flag_on_invalid_rewrite_falls_back_to_deterministic():
    verdict = "Benzer 12 alıcının %25'i iade etmiş."
    client = _StubClient(payload={"answer_tr": (
        "Benzer 12 alıcının %25'i iade etmiş; %80'i memnun."   # %80 invented
    )})
    out = _run(maybe_compose_narrative(
        facts={"verdict_tr": verdict, "evidence_tr": []},
        deterministic_verdict_tr=verdict,
        ai_client=client,
        enabled=True,
    ))
    assert out == verdict
    assert client.calls == 1


def test_flag_on_client_error_falls_back_silently():
    verdict = "Önerilen beden M."
    client = _StubClient(raise_exc=True)
    out = _run(maybe_compose_narrative(
        facts={"verdict_tr": verdict},
        deterministic_verdict_tr=verdict,
        ai_client=client,
        enabled=True,
    ))
    assert out == verdict
    assert client.calls == 1


# ---------------------------------------------------------------------------
# Default settings — flag must be false by default so demos are stable
# ---------------------------------------------------------------------------

def test_default_settings_have_flag_off(monkeypatch):
    # Clear any ambient ENABLE_GEMINI_NARRATIVE the dev shell might carry.
    monkeypatch.delenv("ENABLE_GEMINI_NARRATIVE", raising=False)
    from app.config import get_settings
    get_settings.cache_clear()
    try:
        s = get_settings()
        assert s.enable_gemini_narrative is False
    finally:
        get_settings.cache_clear()
