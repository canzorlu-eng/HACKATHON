"""Shared test fixtures.

Uses SQLite in-memory so no Postgres is required for the test suite.
The image_storage_dir is redirected to a tmp_path to keep the filesystem clean.
The AI client is replaced with MockAIClient so tests never call Gemini.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

import app.models  # noqa: F401 — registers User + Analysis in SQLModel.metadata
from app.ai.client import MockAIClient


@pytest.fixture(name="tmp_storage", autouse=False)
def tmp_storage_fixture(tmp_path, monkeypatch):
    """Point image storage at a temporary directory."""
    monkeypatch.setenv("IMAGE_STORAGE_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


@pytest.fixture(name="db_session")
def db_session_fixture():
    """
    SQLite in-memory session with all tables created.

    StaticPool is required: without it SQLAlchemy opens a new connection for
    each checkout and each `:memory:` connection is an independent empty DB,
    so tables created on one connection are invisible to another.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    from app.db import set_engine
    set_engine(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)
    set_engine(None)  # type: ignore[arg-type]


@pytest.fixture(name="mock_ai_client")
def mock_ai_client_fixture():
    return MockAIClient()


@pytest.fixture(name="client")
def client_fixture(db_session, tmp_storage, mock_ai_client):
    """TestClient with DB, storage, and AI-client overrides applied."""
    from app.main import app
    from app.db import get_session
    from app.ai.client import get_ai_client

    def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_ai_client] = lambda: mock_ai_client
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Reusable fake image bytes (magic-byte correct, minimal size)
# ---------------------------------------------------------------------------

JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
BMP_BYTES = b"BM" + b"\x00" * 64          # BMP — not accepted
TRUNCATED_BYTES = b"\xff\xd8"             # Too short for header read
GARBAGE_BYTES = b"NOTANIMAGE" + b"\x00" * 64
