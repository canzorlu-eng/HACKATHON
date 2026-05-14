"""
JWT authentication dependency.

Trust contract:
- NextAuth on the frontend issues an HS256 JWT signed with NEXTAUTH_SECRET.
- The frontend forwards the JWT in `Authorization: Bearer <token>` on every
  protected backend call.
- This module verifies the signature with the shared secret, extracts
  google_sub + email, and on first sight upserts a `User` row so the rest
  of the pipeline can attach data by a stable internal UUID.

A bad / missing token returns 401. A valid token whose user has no profile
yet still resolves — it's up to individual endpoints to require a complete
profile when they need measurements.
"""

import logging
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlmodel import Session

from app.config import get_settings
from app.db import get_session
from app.models.user import User
from app.repositories.users import UserRepository

logger = logging.getLogger(__name__)

_ALGORITHM = "HS256"


def _decode_token(authorization: Optional[str]) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Oturum açmanız gerekiyor.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1].strip()
    settings = get_settings()
    if not settings.nextauth_secret:
        # Misconfiguration on the backend side — bail out loudly.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sunucu kimlik doğrulama yapılandırması eksik.",
        )

    try:
        payload = jwt.decode(
            token,
            settings.nextauth_secret,
            algorithms=[_ALGORITHM],
            # NextAuth includes its own aud/iss expectations only when
            # configured; we keep verification minimal.
            options={"verify_aud": False, "verify_iss": False},
        )
    except JWTError as exc:
        logger.info("jwt_verify_failed err=%s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya süresi dolmuş oturum.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return payload


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    session: Session = Depends(get_session),
) -> User:
    """
    FastAPI dependency: resolve the authenticated user from the Bearer token.

    On first sight of a Google identity, an empty User row is created so
    later writes can attach to a stable UUID. Subsequent requests find the
    same user by google_sub.
    """
    payload = _decode_token(authorization)

    google_sub = payload.get("sub") or payload.get("googleSub")
    email = payload.get("email")
    name = payload.get("name")

    if not google_sub or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz oturum: Google kimliği bulunamadı.",
        )

    repo = UserRepository(session)
    user = repo.find_or_create_by_google_sub(
        google_sub=google_sub,
        email=email,
        name=name,
    )
    return user
