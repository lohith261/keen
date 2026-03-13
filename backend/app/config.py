"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the KEEN backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────
    environment: str = "development"
    debug: bool = True
    secret_key: str = "CHANGE-ME"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── Supabase ─────────────────────────────────────────
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # ── Database ─────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/keen"

    # ── Redis ────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Security ─────────────────────────────────────────
    credential_encryption_key: str = ""

    # ── AI / LLM ─────────────────────────────────────────
    openai_api_key: str = ""
    gemini_api_key: str = ""
    anthropic_api_key: str = ""

    # ── TinyFish ─────────────────────────────────────────
    tinyfish_api_key: str = ""
    tinyfish_base_url: str = "https://api.tinyfish.io"

    # ── Agent Settings ───────────────────────────────────
    checkpoint_interval_seconds: int = 90
    agent_timeout_seconds: int = 14_400  # 4 hours

    # ── Helpers ──────────────────────────────────────────
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
