"""Table-driven tests for the QA intent router (regex, no LLM)."""

import pytest

from app.ai.qa_intent import route_intent


# Each row: (text, expected_intent). Covers the canonical chip phrasings
# plus free-text variants. Precedence collisions are explicitly tested.
@pytest.mark.parametrize("text,expected", [
    # ── is_big ─────────────────────────────────────────────────────────────
    ("bu büyük mü?",                          "is_big"),
    ("biraz büyük gelir mi acaba",            "is_big"),
    ("bol mu yoksa tam beden mi?",            "is_big"),

    # ── fabric_sweat ───────────────────────────────────────────────────────
    ("kumaş terletir mi?",                    "fabric_sweat"),
    ("yaz için uygun mu?",                    "fabric_sweat"),
    ("nefes alır mı bu kumaş?",               "fabric_sweat"),

    # ── cut_wide ──────────────────────────────────────────────────────────
    ("bu kalıp geniş mi?",                    "cut_wide"),
    ("kesim nasıl, slim mi?",                 "cut_wide"),
    ("oversize mi yoksa regular mi",          "cut_wide"),

    # ── similar_users ─────────────────────────────────────────────────────
    ("benzer kullanıcılar ne yaşamış?",        "similar_users"),
    ("başkaları beğenmiş mi",                  "similar_users"),
    ("benzer alıcıların yorumları nasıl",      "similar_users"),

    # ── return_reasons ────────────────────────────────────────────────────
    ("neden iade etmişler?",                   "return_reasons"),
    ("iade oranı nedir",                       "return_reasons"),
    ("kaçı iade etmiş bu ürünü",               "return_reasons"),

    # ── unsupported ───────────────────────────────────────────────────────
    ("hava nasıl?",                            "unsupported"),
    ("merhaba",                                "unsupported"),
    ("",                                       "unsupported"),
])
def test_route_intent(text, expected):
    assert route_intent(text) == expected


# ---------------------------------------------------------------------------
# Precedence — questions that could match multiple intents must hit the
# more specific bucket first.
# ---------------------------------------------------------------------------

def test_kalip_genis_routes_to_cut_wide_not_is_big():
    # "geniş kalıp" must beat the broader "büyük/bol/geniş" bucket
    assert route_intent("bu kalıp çok geniş mi geliyor sence") == "cut_wide"


def test_iade_with_benzer_keyword_routes_to_return_reasons():
    # return_reasons sits above similar_users — iade is the more specific signal
    assert route_intent("benzer kullanıcılar neden iade etmiş?") == "return_reasons"


def test_kalip_with_turkish_consonant_alternation():
    # Turkish "kalıp" inflects to "kalıbı" — the rule must accept the stem
    # so cut_wide wins over fabric_sweat when the user is really asking
    # about the cut even with kumaş present.
    assert route_intent("kalıp olarak nasıl?") == "cut_wide"
    assert route_intent("kumaşın kalıbı düşük mü") == "cut_wide"
    assert route_intent("kumaş düşük nefes alır mı") == "fabric_sweat"
