"""UC-01 — Create / retrieve user profile (authenticated)."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session

from app.api.auth import get_current_user
from app.config import get_settings
from app.db import get_session
from app.models.user import User
from app.schemas.profile import FitPreference, ProfileResponse
from app.services.image_store import ImageValidationError, validate_and_store

logger = logging.getLogger(__name__)
router = APIRouter()

_VALID_FIT_PREFERENCES = {fp.value for fp in FitPreference}


def _to_response(user: User) -> ProfileResponse:
    return ProfileResponse(
        user_id=user.id,
        height_cm=user.height_cm or 0,
        weight_kg=user.weight_kg or 0,
        fit_preference=FitPreference(user.fit_preference)
        if user.fit_preference
        else FitPreference.regular,
        has_body_image=user.body_image_ref is not None,
        created_at=user.created_at,
    )


@router.post("/profile", response_model=ProfileResponse, status_code=201)
async def upsert_profile(
    height_cm: int = Form(...),
    weight_kg: int = Form(...),
    fit_preference: str = Form(...),
    body_image: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ProfileResponse:
    """
    UC-01: Set or update the authenticated user's measurements + fit preference.

    Creates the body image record if one is uploaded; replaces any previous one.
    Idempotent — calling it again updates the existing profile in-place.
    """
    if not (50 <= height_cm <= 300):
        raise HTTPException(422, detail="Boy değeri 50 ile 300 cm arasında olmalıdır.")
    if not (20 <= weight_kg <= 500):
        raise HTTPException(422, detail="Kilo değeri 20 ile 500 kg arasında olmalıdır.")
    if fit_preference not in _VALID_FIT_PREFERENCES:
        opts = ", ".join(sorted(_VALID_FIT_PREFERENCES))
        raise HTTPException(422, detail=f"Geçersiz uyum tercihi. Seçenekler: {opts}.")

    image_ref: Optional[str] = current_user.body_image_ref
    if body_image and body_image.filename:
        settings = get_settings()
        try:
            image_ref = await validate_and_store(
                body_image,
                subfolder="body",
                storage_dir=settings.image_storage_dir,
                max_upload_mb=settings.max_upload_mb,
            )
        except ImageValidationError as exc:
            raise HTTPException(422, detail=str(exc)) from exc

    current_user.height_cm = height_cm
    current_user.weight_kg = weight_kg
    current_user.fit_preference = fit_preference
    current_user.body_image_ref = image_ref
    session.add(current_user)
    session.commit()
    session.refresh(current_user)

    logger.info(
        "profile_upserted user_id=%s has_image=%s",
        current_user.id,
        image_ref is not None,
    )

    return _to_response(current_user)


@router.get("/profile/me", response_model=ProfileResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> ProfileResponse:
    """Return the authenticated user's profile.

    Returns 404 when the user is authenticated but hasn't completed onboarding
    (no measurements yet) — the frontend uses that to gate onboarding.
    """
    if current_user.height_cm is None or current_user.weight_kg is None:
        raise HTTPException(404, detail="Profil henüz oluşturulmamış.")
    return _to_response(current_user)
