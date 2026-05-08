"""Langfuse callback handler factory + RunnableConfig builder.

Langfuse v3+ has shifted to an OpenTelemetry backbone: you initialise a
single global `Langfuse` client at startup, then `CallbackHandler()` is a
near-empty wrapper that picks up that client. Spans flow through the
LangChain → LangGraph runnable tree via contextvars, so we only need to
attach the handler at the **outermost** `graph.ainvoke` — all child LLM
calls, retries, retrievals, and tool invocations are captured automatically.

Design choices
──────────────
1. **Graceful degradation** — if either key is missing, we log once and
   skip instrumentation. The system works without observability for
   local dev where the user hasn't created Langfuse keys yet.
2. **Session grouping** — `metadata.langfuse_session_id = session_id` lets
   the UI group every turn of a conversation under one trace timeline,
   which is exactly what an interviewer wants to see during demo.
3. **Environment + release tags** — so `dev` traces don't pollute future
   `prod` dashboards once we deploy.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

_initialised: bool = False


def init_langfuse() -> bool:
    """Initialise the global Langfuse client. Idempotent.

    Returns True if instrumentation is active, False if the keys are
    missing (in which case the system runs without traces).
    """
    global _initialised  # noqa: PLW0603
    if _initialised:
        return True

    settings = get_settings()
    public_key = settings.langfuse_public_key.strip()
    secret_key = settings.langfuse_secret_key.get_secret_value().strip()

    if not public_key or not secret_key:
        log.info("langfuse.disabled", reason="keys_missing")
        return False

    from langfuse import Langfuse  # noqa: PLC0415  (lazy import — heavy module)

    Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=settings.langfuse_host,
        environment=settings.app_env,
        release="deepbaht-0.1.0",
    )
    _initialised = True
    log.info(
        "langfuse.initialised",
        host=settings.langfuse_host,
        environment=settings.app_env,
    )
    return True


@lru_cache(maxsize=1)
def get_callback_handler() -> Any | None:
    """Return a singleton Langfuse `CallbackHandler`, or None if not configured."""
    if not init_langfuse():
        return None
    from langfuse.langchain import CallbackHandler  # noqa: PLC0415

    return CallbackHandler()


def build_config(
    session_id: str,
    *,
    user_id: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Build a `RunnableConfig` that ships LangChain/LangGraph traces to Langfuse,
    grouped by `session_id`.

    Returns an empty dict when Langfuse is not configured — `graph.ainvoke({}, config={})`
    is identical to a plain call, so the supervisor doesn't need a branch.
    """
    handler = get_callback_handler()
    if handler is None:
        return {}
    return {
        "callbacks": [handler],
        "metadata": {
            "langfuse_session_id": session_id,
            "langfuse_user_id": user_id or "anon",
            "langfuse_tags": tags or ["deepbaht", get_settings().app_env],
        },
    }


def flush() -> None:
    """Force-flush pending traces. Call on application shutdown so we don't
    drop the last few requests when the container is recreated."""
    if not _initialised:
        return
    try:
        from langfuse import get_client  # noqa: PLC0415

        get_client().flush()
        log.info("langfuse.flushed")
    except Exception as exc:  # noqa: BLE001
        log.warning("langfuse.flush_failed", error=str(exc))
