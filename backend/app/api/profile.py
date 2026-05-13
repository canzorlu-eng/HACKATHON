"""UC-01 — Create / retrieve user profile."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session

from app.config import get_settings
from app.db import get_session
from app.models.user import User
from app.repositories.users import UserRepository
from app.schemas.profile import FitPreference, ProfileResponse
from app.services.image_store import ImageValidationError, validate_and_store

logger = logging.getLogger(__name__)
router = APIRouter()

_VALID_FIT_PREFERENCES = {fp.value for fp in FitPreference}


@router.post("/profile", response_model=ProfileResponse, status_code=201)
async def create_profile(
    height_cm: int = Form(...),
    weight_kg: int = Form(...),
    fit_preference: str = Form(...),
    body_image: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session),
) -> ProfileResponse:
    """
    UC-01: Create a personalized fit profile.
    Accepts body measurements, fit preference, and an optional body image.
    """
    if not (50 <= height_cm <= 300):
        raise HTTPException(422, detail="Boy değeri 50 ile 300 cm arasında olmalıdır.")
    if not (20 <= weight_kg <= 500):
        raise HTTPException(422, detail="Kilo değeri 20 ile 500 kg arasında olmalıdır.")
    if fit_preference not in _VALID_FIT_PREFERENCES:
        opts = ", ".join(sorted(_VALID_FIT_PREFERENCES))
        raise HTTPException(422, detail=f"Geçersiz uyum tercihi. Seçenekler: {opts}.")

    image_ref: Optional[str] = None
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

    user = User(
        height_cm=height_cm,
        weight_kg=weight_kg,
        fit_preference=fit_preference,
        body_image_ref=image_ref,
    )
    repo = UserRepository(session)
    user = repo.create(user)

    # Privacy: log user_id and presence of image only — no height/weight
    logger.info("profile_created user_id=%s has_image=%s", user.id, image_ref is not None)

    return ProfileResponse(
        user_id=user.id,
        height_cm=user.height_cm,
        weight_kg=user.weight_kg,
        fit_preference=FitPreference(user.fit_preference),
        has_body_image=user.body_image_ref is not None,
        created_at=user.created_at,
    )


@router.get("/profile/{user_id}", response_model=ProfileResponse)
def get_profile(
    user_id: UUID,
    session: Session = Depends(get_session),
) -> ProfileResponse:
    """Return an existing profile by user_id."""
    repo = UserRepository(session)
    user = repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(404, detail="Kullanıcı profili bulunamadı.")

    return ProfileResponse(
        user_id=user.id,
        height_cm=user.height_cm,
        weight_kg=user.weight_kg,
        fit_preference=FitPreference(user.fit_preference),
        has_body_image=user.body_image_ref is not None,
        created_at=user.created_at,
    )
