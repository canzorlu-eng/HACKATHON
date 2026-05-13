from typing import Generator

from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        from app.config import get_settings

        s = get_settings()
        url = (
            f"postgresql+psycopg2://{s.postgres_user}:{s.postgres_password}"
            f"@{s.postgres_host}:{s.postgres_port}/{s.postgres_db}"
        )
        _engine = create_engine(url, echo=(s.app_env == "dev"))
    return _engine


def set_engine(engine: Engine) -> None:
    """Override the engine — used by tests to inject SQLite."""
    global _engine
    _engine = engine


def create_db_tables() -> None:
    import app.models  # noqa: F401 — registers all SQLModel metadata

    SQLModel.metadata.create_all(get_engine())


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session
