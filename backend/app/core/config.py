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
    app_name: str = "DeepBaht"
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:4001"])

    # ── Typhoon (primary LLM) ────────────────────────────────────────────────
    # Free tier exposes only `typhoon-v2.5-30b-a3b-instruct` for chat (verified
    # via /v1/models on 2026-05-08). The two-tier code path is preserved so we
    # can drop in a smaller fast model if Pro tier enables one later.
    # Rate limit (per https://docs.opentyphoon.ai/en/rate-limits/): 5 RPS / 200 RPM.
    typhoon_api_key: SecretStr = SecretStr("replace-me")
    typhoon_base_url: str = "https://api.opentyphoon.ai/v1"
    typhoon_chat_model: str = "typhoon-v2.5-30b-a3b-instruct"   # reasoning, advisor
    typhoon_fast_model: str = "typhoon-v2.5-30b-a3b-instruct"   # routing, classification (same on free tier)

    # ── Fallback (Ollama) ────────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://deepbaht:deepbaht_dev@localhost:4432/deepbaht"
    # Read-only role for the Text-to-SQL agent (least privilege).
    database_url_ro: str = (
        "postgresql+asyncpg://deepbaht_ro:deepbaht_ro_dev@localhost:4432/deepbaht"
    )

    # Demo authentication shortcut — in production, scope from session token.
    demo_customer_id: str = "C0001"

    # ── MCP ──────────────────────────────────────────────────────────────────
    mcp_server_url: str = "http://localhost:4765"

    # ── LangFuse ─────────────────────────────────────────────────────────────
    langfuse_host: str = "http://localhost:4002"
    langfuse_public_key: str = ""
    langfuse_secret_key: SecretStr = SecretStr("")

    # ── Embeddings ───────────────────────────────────────────────────────────
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024

    # ── ASR ──────────────────────────────────────────────────────────────────
    # `api`   = call OpenTyphoon (free tier, 100 RPM). `local` = HF transformers.
    asr_backend: Literal["api", "local"] = "api"
    asr_model_api: str = "typhoon-asr-realtime"
    asr_model_local: str = "scb10x/typhoon-asr-realtime"
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
