"""Integration tests for POST /api/v1/qa.

Uses the same client/auth/MockAIClient setup as the rest of the suite.
The MockAIClient's analyze_garment returns category=shirt, fit_type=regular,
brand_sizing_tendency=standart — so cohort lookups in tests should fall
back to stage B if the body envelope doesn't match.
"""

from tests.conftest import JPEG_BYTES


def _onboard(client, auth_headers, height=170, weight=65, fit="regular"):
    r = client.post(
        "/api/v1/profile",
        data={"height_cm": str(height), "weight_kg": str(weight), "fit_preference": fit},
        headers=auth_headers,
    )
    assert r.status_code == 201


def _upload_and_get_id(client, auth_headers):
    r = client.post(
        "/api/v1/analyze",
        files={"garment_image": ("shirt.jpg", JPEG_BYTES, "image/jpeg")},
        headers=auth_headers,
    )
    assert r.status_code == 202
    return r.json()["analysis_id"]


# ---------------------------------------------------------------------------
# Auth + ownership
# ---------------------------------------------------------------------------

def test_qa_unauthenticated_returns_401(client):
    r = client.post("/api/v1/qa", data={"analysis_id": "00000000-0000-0000-0000-000000000000", "text": "bu büyük mü?"})
    assert r.status_code == 401


def test_qa_unknown_analysis_returns_404(client, auth_headers):
    _onboard(client, auth_headers)
    r = client.post(
        "/api/v1/qa",
        data={"analysis_id": "00000000-0000-0000-0000-000000000000", "text": "bu büyük mü?"},
        headers=auth_headers,
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# All 5 supported intents — chip phrasings must route + return non-empty answer
# ---------------------------------------------------------------------------

def _post_qa(client, headers, aid, text):
    return client.post(
        "/api/v1/qa",
        data={"analysis_id": aid, "text": text},
        headers=headers,
    )


def test_is_big_intent_returns_grounded_answer(client, auth_headers):
    _onboard(client, auth_headers)
    aid = _upload_and_get_id(client, auth_headers)
    r = _post_qa(client, auth_headers, aid, "bu büyük mü?")
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "is_big"
    assert len(body["answer_tr"]) > 10
    assert body["confidence_band"] in ("low", "medium", "high")
    assert len(body["evidence_tr"]) >= 1


def test_fabric_sweat_intent(client, auth_headers):
    _onboard(client, auth_headers)
    aid = _upload_and_get_id(client, auth_headers)
    r = _post_qa(client, auth_headers, aid, "kumaş terletir mi?")
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "fabric_sweat"
    assert any(kw in body["answer_tr"].lower()
               for kw in ("terlet", "nefes", "kumaş", "yaz"))


def test_cut_wide_intent(client, auth_headers):
    _onboard(client, auth_headers)
    aid = _upload_and_get_id(client, auth_headers)
    r = _post_qa(client, auth_headers, aid, "bu kalıp geniş mi?")
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "cut_wide"
    assert body["confidence_band"] == "high"


def test_similar_users_intent_returns_cohort_scope(client, auth_headers):
    _onboard(client, auth_headers)
    aid = _upload_and_get_id(client, auth_headers)
    r = _post_qa(client, auth_headers, aid, "benzer kullanıcılar ne yaşamış?")
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "similar_users"
    # cohort_scope_tr must be present even when band is low
    assert body["cohort_scope_tr"] is not None


def test_return_reasons_intent_returns_cohort_scope(client, auth_headers):
    _onboard(client, auth_headers)
    aid = _upload_and_get_id(client, auth_headers)
    r = _post_qa(client, auth_headers, aid, "neden iade etmişler?")
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "return_reasons"
    assert body["cohort_scope_tr"] is not None


# ---------------------------------------------------------------------------
# Honesty rail — low confidence must NEVER include a fabricated percentage
# ---------------------------------------------------------------------------

def test_low_confidence_cohort_does_not_publish_fabricated_pct(client, auth_headers):
    # Use weird body metrics so the cohort lookup falls through to a tiny
    # stage-B (or even none) → band must be "low" → answer must not contain
    # any "%X" token.
    _onboard(client, auth_headers, height=199, weight=140)
    aid = _upload_and_get_id(client, auth_headers)
    r = _post_qa(client, auth_headers, aid, "neden iade etmişler?")
    assert r.status_code == 200
    body = r.json()
    if body["confidence_band"] == "low":
        assert "%" not in body["answer_tr"], (
            f"Low-confidence answer must not contain a percentage: "
            f"{body['answer_tr']}"
        )


# ---------------------------------------------------------------------------
# Unsupported fallback
# ---------------------------------------------------------------------------

def test_unsupported_question_routes_to_refusal(client, auth_headers):
    _onboard(client, auth_headers)
    aid = _upload_and_get_id(client, auth_headers)
    r = _post_qa(client, auth_headers, aid, "hava nasıl bugün?")
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "unsupported"
    assert body["confidence_band"] == "low"
    assert "HIWALOY" in body["answer_tr"]


# ---------------------------------------------------------------------------
# Garment-invalid gate — QA must refuse without running fact collectors
# when the original analysis flagged the upload as not a garment.
# ---------------------------------------------------------------------------

def test_garment_invalid_analysis_returns_polite_refusal(
    client, auth_headers, db_session,
):
    from uuid import uuid4
    from app.models.analysis import Analysis
    from app.repositories.users import UserRepository

    _onboard(client, auth_headers)

    user = UserRepository(db_session).get_by_google_sub("test-google-sub-1")
    assert user is not None

    # Persist a garment-invalid analysis directly — mirrors what the pipeline
    # writes when garment_analysis.is_garment == False.
    a = Analysis(
        id=uuid4(),
        user_id=user.id,
        garment_image_ref="invalid.jpg",
        recommended_size=None,        # ← the garment-invalid signal
        recommended_confidence=None,
        risk_level=None,
        formatted_response={
            "recommended_size": None,
            "confidence_score": None,
            "explanation_tr": "Yüklenen görselde tanınabilir bir kıyafet bulunamadı.",
            "risk_level": None,
            "risk_factors_tr": [],
            "community_insights_tr": [],
        },
    )
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)

    # All 5 chip phrasings must route to the polite refusal — never to a
    # cohort lookup or a Gemini call that would invent content.
    for q in ("bu büyük mü?", "kumaş terletir mi?", "bu kalıp geniş mi?",
              "benzer kullanıcılar ne yaşamış?", "neden iade etmişler?"):
        r = _post_qa(client, auth_headers, str(a.id), q)
        assert r.status_code == 200, (q, r.text)
        body = r.json()
        assert body["intent"] == "unsupported"
        assert body["confidence_band"] == "low"
        assert body["evidence_tr"] == []
        # Refusal message must mention "kıyafet" — content stays stable.
        assert "kıyafet" in body["answer_tr"].lower()
