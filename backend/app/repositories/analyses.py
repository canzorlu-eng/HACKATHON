from uuid import UUID

from sqlmodel import Session, select

from app.models.analysis import Analysis


class AnalysisRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, analysis: Analysis) -> Analysis:
        self._session.add(analysis)
        self._session.commit()
        self._session.refresh(analysis)
        return analysis

    def get_by_id(self, analysis_id: UUID) -> Analysis | None:
        return self._session.get(Analysis, analysis_id)

    def list_by_user(self, user_id: UUID, limit: int = 50) -> list[Analysis]:
        stmt = (
            select(Analysis)
            .where(Analysis.user_id == user_id)
            .order_by(Analysis.created_at.desc())
            .limit(limit)
        )
        return list(self._session.exec(stmt).all())

    def get_overflow(self, user_id: UUID, keep: int) -> list[Analysis]:
        """Return analyses beyond the most recent `keep` for this user.

        Used by analyze.py to prune the user's history down to the latest N
        records whenever a new analysis is created.
        """
        stmt = (
            select(Analysis)
            .where(Analysis.user_id == user_id)
            .order_by(Analysis.created_at.desc())
            .offset(keep)
        )
        return list(self._session.exec(stmt).all())

    def delete(self, analysis: Analysis) -> None:
        self._session.delete(analysis)
        self._session.commit()
