from typing import Optional
from uuid import UUID

from sqlmodel import Session, select

from app.models.user import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, user: User) -> User:
        self._session.add(user)
        self._session.commit()
        self._session.refresh(user)
        return user

    def get_by_id(self, user_id: UUID) -> User | None:
        return self._session.get(User, user_id)

    def get_by_google_sub(self, google_sub: str) -> User | None:
        stmt = select(User).where(User.google_sub == google_sub)
        return self._session.exec(stmt).first()

    def find_or_create_by_google_sub(
        self,
        google_sub: str,
        email: str,
        name: Optional[str] = None,
    ) -> User:
        """
        Idempotent upsert keyed on google_sub.

        First sight creates a User with no measurements. Subsequent sightings
        return the same row (and keep email/name in sync with Google).
        """
        user = self.get_by_google_sub(google_sub)
        if user is None:
            user = User(google_sub=google_sub, email=email, name=name)
            self._session.add(user)
            self._session.commit()
            self._session.refresh(user)
            return user

        # Keep email + name in sync with Google in case the user changed them.
        if user.email != email or user.name != name:
            user.email = email
            user.name = name
            self._session.add(user)
            self._session.commit()
            self._session.refresh(user)
        return user

    def update_body_image_ref(self, user_id: UUID, image_ref: str) -> User | None:
        user = self.get_by_id(user_id)
        if user is None:
            return None
        user.body_image_ref = image_ref
        self._session.add(user)
        self._session.commit()
        self._session.refresh(user)
        return user
