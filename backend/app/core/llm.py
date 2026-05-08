"""LLM client factory — Typhoon as primary, Ollama as offline fallback.

Typhoon (SCB 10X) exposes an OpenAI-compatible API, so we reuse the standard
LangChain `ChatOpenAI` class with custom `base_url`. This means every LangChain
/ LangGraph integration works out of the box (tool calling, structured output,
streaming) — no custom adapter needed.

Two models are exposed because not every node in a multi-agent graph needs
the 70B instruct model:
  - `chat`  → high quality reasoning (Supervisor, Investment Advisor)
  - `fast`  → routing, classification, query rewriting, function calling
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from langchain_openai import ChatOpenAI

from app.core.config import Settings, get_settings

ModelTier = Literal["chat", "fast"]


def _build_typhoon(settings: Settings, tier: ModelTier) -> ChatOpenAI:
    model = (
        settings.typhoon_chat_model if tier == "chat" else settings.typhoon_fast_model
    )
    return ChatOpenAI(
        model=model,
        api_key=settings.typhoon_api_key.get_secret_value(),
        base_url=settings.typhoon_base_url,
        temperature=0.2 if tier == "chat" else 0.0,
        timeout=60,
        max_retries=2,
    )


@lru_cache(maxsize=4)
def get_llm(tier: ModelTier = "chat") -> ChatOpenAI:
    """Return a cached Typhoon chat model.

    Cached because re-instantiating LangChain LLM clients on every request
    is wasteful and prevents underlying httpx connection pools from reusing
    keep-alive connections.
    """
    return _build_typhoon(get_settings(), tier)
