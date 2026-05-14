"""Tests for the /stylist endpoint."""

from app.services import catalog


def _onboard(client, auth_headers, **overrides):
    data = {"height_cm": "175", "weight_kg": "70", "fit_preference": "oversize"}
    data.update({k: str(v) for k, v in overrides.items()})
    r = client.post("/api/v1/profile", data=data, headers=auth_headers)
    assert r.status_code == 201


# ---------------------------------------------------------------------------
# Auth + profile gating
# ---------------------------------------------------------------------------

def test_stylist_unauthenticated_returns_401(client):
    r = client.post("/api/v1/stylist", data={"query": "ucuz tişört"})
    assert r.status_code == 401


def test_stylist_without_profile_returns_409(client, auth_headers):
    r = client.post(
        "/api/v1/stylist",
        data={"query": "oversize tişört"},
        headers=auth_headers,
    )
    assert r.status_code == 409
    assert "Profil" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_stylist_returns_three_grounded_picks(client, auth_headers):
    _onboard(client, auth_headers)
    r = client.post(
        "/api/v1/stylist",
        data={"query": "oversize tişört öner"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["suggestions"]) == 3
    # Every pick must hydrate against the real catalog — no fabrication.
    catalog_ids = {it["id"] for it in catalog.all_items()}
    for s in body["suggestions"]:
        assert s["garment_id"] in catalog_ids
        assert s["name"]
        assert s["brand"]
        assert s["price_tl"] > 0
        assert s["reason_tr"]
    assert body["stylist_note_tr"]
    assert body["query_echo"] == "oversize tişört öner"


def test_stylist_respects_price_ceiling(client, auth_headers):
    _onboard(client, auth_headers)
    r = client.post(
        "/api/v1/stylist",
        data={"query": "300 TL altında basic tişört"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["max_price_tl"] == 300
    for s in body["suggestions"]:
        assert s["price_tl"] <= 300, f"{s['garment_id']} priced {s['price_tl']} > 300"


def test_stylist_returns_empty_message_when_filter_excludes_all(client, auth_headers):
    _onboard(client, auth_headers)
    r = client.post(
        "/api/v1/stylist",
        data={"query": "10 TL altında ceket"},  # impossible
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["suggestions"] == []
    assert "bulunamadı" in body["stylist_note_tr"].lower()


def test_stylist_query_length_validation(client, auth_headers):
    _onboard(client, auth_headers)
    r = client.post(
        "/api/v1/stylist",
        data={"query": "x" * 1000},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_stylist_off_topic_returns_polite_refusal(client, auth_headers, monkeypatch):
    """Non-fashion queries must short-circuit with the fixed Turkish refusal."""
    _onboard(client, auth_headers)

    # Force the AI client to flag the request as off-topic regardless of
    # the input (mirroring what Gemini's scope gate will do in production).
    async def fake_stylist_pick(self, *args, **kwargs):  # noqa: ARG002
        return {
            "is_fashion_request": False,
            "picks": [],
            "stylist_note_tr": "",
            "uncertainty_tr": None,
        }

    from app.ai.client import MockAIClient
    monkeypatch.setattr(MockAIClient, "stylist_pick", fake_stylist_pick)

    r = client.post(
        "/api/v1/stylist",
        data={"query": "Python ile bir hesap makinesi kodu yaz"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["off_topic"] is True
    assert body["suggestions"] == []
    assert "HIWALOY Stilist" in body["stylist_note_tr"]
    assert "giyim" in body["stylist_note_tr"]


# ---------------------------------------------------------------------------
# Price extraction helper
# ---------------------------------------------------------------------------

class TestExtractMaxPrice:
    def test_explicit_override_wins(self):
        assert catalog.extract_max_price_tl("anything", 250) == 250

    def test_TL_pattern(self):
        assert catalog.extract_max_price_tl("500 TL altında bir tişört") == 500

    def test_lira_pattern(self):
        assert catalog.extract_max_price_tl("300 lira civarı") == 300

    def test_ucuz_keyword(self):
        assert catalog.extract_max_price_tl("ucuz bir gömlek") == 400

    def test_no_signal_returns_none(self):
        assert catalog.extract_max_price_tl("rahat bir kombin") is None


# ---------------------------------------------------------------------------
# Catalog filter
# ---------------------------------------------------------------------------

class TestFilterShortlist:
    def test_price_filter_applied(self):
        out = catalog.filter_shortlist(query="tişört", max_price_tl=300)
        assert out
        for it in out:
            assert it["price_tl"] <= 300

    def test_category_detected_from_query(self):
        out = catalog.filter_shortlist(query="ceket öner")
        assert out
        for it in out:
            assert it["category"] == "jacket"

    def test_fit_preference_promotes_matching_items(self):
        out = catalog.filter_shortlist(
            query="tişört",
            user_fit_preference="oversize",
            limit=12,
        )
        # The first match in the result should be an oversize tshirt if the
        # catalog contains one.
        assert out[0]["fit_type"] == "oversize" or all(
            it["fit_type"] != "oversize" for it in out
        )
