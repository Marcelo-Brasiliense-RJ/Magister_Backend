"""Configuracao central lida do .env via pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "development"
    cors_allow_origins: str = "http://localhost:5173"

    # Auth admin (JWT)
    jwt_secret: str = "dev-secret-change-me"
    jwt_expire_minutes: int = 60
    admin_username: str = "admin"
    admin_password_hash: str = ""

    # Persistencia
    database_url: str = "sqlite:///./magister.db"

    # Conversa / limites
    history_window: int = 40
    max_output_tokens: int = 800
    max_tokens_per_session: int = 50000
    chat_rate_limit_per_min: int = 20

    # Fontes (SSRF guard)
    fetch_timeout_seconds: float = 8.0
    fetch_max_bytes: int = 200_000

    # LLM router (lista JSON, ordenada por custo/prioridade)
    llm_providers: list[dict] = []
    # Mapa opcional tarefa->modelo (knowledge|persona|guardrail|summarize)
    llm_task_models: dict = {}

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
