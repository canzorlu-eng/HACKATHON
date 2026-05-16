from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="dev")
    log_level: str = Field(default="INFO")
    cors_origins: str = Field(default="http://localhost:3000")
    max_upload_mb: int = Field(default=8)
    image_retention_hours: int = Field(default=24)
    image_storage_dir: str = Field(default="./var/images")

    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="hiwaloy")
    postgres_user: str = Field(default="hiwaloy")
    postgres_password: str = Field(default="")

    chroma_host: str = Field(default="localhost")
    chroma_port: int = Field(default=8001)

    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="")
    embedding_model: str = Field(default="")

    # Shared HS256 secret used by NextAuth (frontend) to sign session JWTs
    # and by FastAPI to verify them. Must match NEXTAUTH_SECRET in frontend.
    nextauth_secret: str = Field(default="")

    demo_mode: bool = Field(default=False)

    # Off by default — deterministic verdict_tr from the fact collectors is
    # the primary response path. When true, the /qa endpoint runs an optional
    # Gemini narrative-rewrite pass that is presentation-only: it cannot
    # change facts, sizes, or percentages. Any rewrite containing a number
    # absent from the deterministic verdict is rejected by the honesty rail
    # in app.ai.qa_narrative and we fall back to the deterministic answer.
    enable_gemini_narrative: bool = Field(default=False)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
