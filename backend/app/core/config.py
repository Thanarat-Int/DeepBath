"""Centralised application settings loaded from environment / .env file.

Using pydantic-settings means every config value is **typed and validated** at
startup — a missing/invalid env var fails fast instead of crashing mid-request.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings. Read once at startup and reused via `get_settings()`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = "AutoX-SCB-AI"
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # ── Typhoon (primary LLM) ────────────────────────────────────────────────
    typhoon_api_key: SecretStr = SecretStr("replace-me")
    typhoon_base_url: str = "https://api.opentyphoon.ai/v1"
    typhoon_chat_model: str = "typhoon-v2-70b-instruct"
    typhoon_fast_model: str = "typhoon-v2-8b-instruct"

    # ── Fallback (Ollama) ────────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://autox:autox_dev@localhost:5432/autox"

    # ── MCP ──────────────────────────────────────────────────────────────────
    mcp_server_url: str = "http://localhost:8765"

    # ── LangFuse ─────────────────────────────────────────────────────────────
    langfuse_host: str = "http://localhost:3001"
    langfuse_public_key: str = ""
    langfuse_secret_key: SecretStr = SecretStr("")

    # ── Embeddings ───────────────────────────────────────────────────────────
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024

    # ── ASR ──────────────────────────────────────────────────────────────────
    asr_model: str = "scb10x/typhoon-asr-realtime"
    asr_device: Literal["cpu", "cuda"] = "cpu"

    # ── Safety ───────────────────────────────────────────────────────────────
    guardrails_enabled: bool = True
    max_input_tokens: int = 4000

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton accessor — used as a FastAPI dependency."""
    return Settings()
