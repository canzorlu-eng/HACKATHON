import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analyze import router as analyze_router
from app.api.health import router as health_router
from app.api.history import router as history_router
from app.api.profile import router as profile_router
from app.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup; nothing to tear down on shutdown."""
    try:
        from app.db import create_db_tables
        create_db_tables()
        logger.info("db_tables_ready")
    except Exception:
        logger.exception(
            "db_startup_failed — continuing without table creation "
            "(expected in test mode with injected SQLite engine)"
        )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="HIWALOY API",
        version="0.1.0",
        description="HIWALOY backend — fit prediction and purchase risk analysis.",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    application.include_router(health_router, prefix="/api/v1")
    application.include_router(profile_router, prefix="/api/v1")
    application.include_router(analyze_router, prefix="/api/v1")
    application.include_router(history_router, prefix="/api/v1")
    return application


app = create_app()
