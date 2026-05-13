from uuid import UUID

from sqlmodel import Session

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

    def update_body_image_ref(self, user_id: UUID, image_ref: str) -> User | None:
        user = self.get_by_id(user_id)
        if user is None:
            return None
        user.body_image_ref = image_ref
        self._session.add(user)
        self._session.commit()
        self._session.refresh(user)
        return user
