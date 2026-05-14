"""AI Stylist endpoint — grounded outfit recommendations from the local catalog."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlmodel import Session

from app.ai.client import AIClient, get_ai_client
from app.api.auth import get_current_user
from app.db import get_session
from app.models.user import User
from app.repositories.analyses import AnalysisRepository
from app.schemas.stylist import StylistResponse, StylistSuggestion
from app.services import catalog

logger = logging.getLogger(__name__)
router = APIRouter()

_MAX_PICKS = 3
_MAX_QUERY_LEN = 280

# Fixed Turkish refusal — used when Gemini's scope gate says the request is
# not about clothing. Keeping the wording in code (not in the prompt) means
# the user gets the same honest, short response every time, with no LLM drift.
_OFF_TOPIC_NOTE_TR = (
    "Bu konuda yardımcı olamam. HIWALOY Stilist yalnızca giyim, kombin ve "
    "beden uyumu önerileri sunar — başka bir konuda destek veremem."
)


def _profile_dict(user: User) -> dict:
    return {
        "height_cm": user.height_cm,
        "weight_kg": user.weight_kg,
        "fit_preference": user.fit_preference,
    }


def _history_snapshot(session: Session, user_id) -> list[dict]:
    repo = AnalysisRepository(session)
    rows = repo.list_by_user(user_id, limit=3)
    return [
        {
            "recommended_size": r.recommended_size,
            "risk_level": r.risk_level,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


def _hydrate(pick: dict) -> Optional[StylistSuggestion]:
    item = catalog.get_by_id(pick.get("garment_id", ""))
    if item is None:
        return None
    return StylistSuggestion(
        garment_id=item["id"],
        name=item["name"],
        brand=item["brand"],
        category=item["category"],
        fit_type=item["fit_type"],
        fabric=item["fabric"],
        price_tl=item["price_tl"],
        reason_tr=pick.get("reason_tr", "").strip(),
        fit_warning_tr=(pick.get("fit_warning_tr") or None),
    )


@router.post("/stylist", response_model=StylistResponse, status_code=200)
async def stylist(
    query: str = Form(..., min_length=1, max_length=_MAX_QUERY_LEN),
    max_price_tl: Optional[int] = Form(default=None, ge=1),
    session: Session = Depends(get_session),
    ai_client: AIClient = Depends(get_ai_client),
    current_user: User = Depends(get_current_user),
) -> StylistResponse:
    """
    AI-powered personal-shopping assistant.

    Picks exactly 3 items from the local catalog grounded in the user's body
    profile, fit preference, recent analyses, and an optional price ceiling.
    Gemini reasons over a pre-filtered shortlist — it cannot invent products.
    """
    if (
        current_user.height_cm is None
        or current_user.weight_kg is None
        or current_user.fit_preference is None
    ):
        raise HTTPException(
            status_code=409,
            detail="Profilinizi tamamlayın: boy, kilo ve tercih edilen kesim gerekli.",
        )

    parsed_max_price = catalog.extract_max_price_tl(query, max_price_tl)
    shortlist = catalog.filter_shortlist(
        query=query,
        max_price_tl=parsed_max_price,
        user_fit_preference=current_user.fit_preference,
    )

    if not shortlist:
        return StylistResponse(
            suggestions=[],
            stylist_note_tr=(
                "Belirttiğin kriterlere uyan bir ürün katalogda bulunamadı. "
                "Bütçeyi veya kategoriyi gevşeterek tekrar dener misin?"
            ),
            uncertainty_tr="Filtreler boş bir liste döndürdü.",
            query_echo=query,
            max_price_tl=parsed_max_price,
        )

    profile = _profile_dict(current_user)
    history = _history_snapshot(session, current_user.id)

    try:
        ai_result = await ai_client.stylist_pick(
            query=query,
            profile=profile,
            history=history,
            shortlist=shortlist,
        )
    except Exception:
        logger.exception("stylist_pick_failed user_id=%s", current_user.id)
        raise HTTPException(
            status_code=502,
            detail="Stilist şu an yanıt veremiyor. Lütfen biraz sonra tekrar deneyin.",
        )

    # Scope gate — if Gemini flagged the request as not-fashion, return a
    # fixed Turkish refusal instead of forcing 3 picks.
    if ai_result.get("is_fashion_request") is False:
        logger.info(
            "stylist_off_topic user_id=%s query_len=%d",
            current_user.id, len(query),
        )
        return StylistResponse(
            suggestions=[],
            stylist_note_tr=_OFF_TOPIC_NOTE_TR,
            uncertainty_tr=None,
            query_echo=query,
            max_price_tl=parsed_max_price,
            off_topic=True,
        )

    raw_picks = ai_result.get("picks", [])[:_MAX_PICKS]
    suggestions: list[StylistSuggestion] = []
    for p in raw_picks:
        hydrated = _hydrate(p)
        if hydrated is not None:
            suggestions.append(hydrated)

    note = ai_result.get("stylist_note_tr") or "Senin için seçim hazırlandı."
    unc = ai_result.get("uncertainty_tr")
    if len(suggestions) < _MAX_PICKS:
        extra = f"Sadece {len(suggestions)} ürün eşleşti."
        unc = f"{unc} {extra}".strip() if unc else extra

    logger.info(
        "stylist_response user_id=%s picks=%d shortlist=%d max_price=%s",
        current_user.id, len(suggestions), len(shortlist), parsed_max_price,
    )

    return StylistResponse(
        suggestions=suggestions,
        stylist_note_tr=note,
        uncertainty_tr=unc,
        query_echo=query,
        max_price_tl=parsed_max_price,
    )
