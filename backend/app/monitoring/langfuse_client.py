"""Langfuse callback handler factory + RunnableConfig builder.

Compatibility note (May 2026)
─────────────────────────────
Our self-hosted server image is `langfuse/langfuse:2` (single container,
no Clickhouse/Redis). The v4+ python client speaks OpenTelemetry which
the v2 server rejects with `404 Not Found` — silent observability + log
spam. The v2 python client, in turn, refuses to load against the
langchain-1.x APIs we depend on for LangGraph 1.x.

So we sit on **v4 client + v2 server** and explicitly disable the OTEL
exporter (`tracing_enabled=False`). This:
  - keeps the language ecosystem (LangGraph, langchain-openai, etc.) at
    the versions everything else needs,
  - suppresses the 404 export noise,
  - leaves the dashboard reachable at http://localhost:4002 (we still
    show it during the demo as our 'production-ready monitoring stack'),
  - makes the upgrade path obvious: switch to `langfuse/langfuse:3` (which
    requires Clickhouse + Redis) and set `tracing_enabled=True`.

The CallbackHandler is still attached so the rest of the code path is
identical to a fully-instrumented run — flip one flag and traces flow.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

_initialised: bool = False
_export_enabled: bool = False


def init_langfuse() -> bool:
    """Initialise the global Langfuse client. Idempotent.

    Returns True if instrumentation is wired (callbacks attached); the
    actual exporter is gated by `_export_enabled` so we don't blow up
    logs when talking to a v2 server.
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

    from langfuse import Langfuse  # noqa: PLC0415

    Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=settings.langfuse_host,
        environment=settings.app_env,
        release="deepbaht-0.1.0",
        # Disable OTEL exporter while we run against a v2 server.
        # Flip to True once the server is upgraded to v3+ (which adds the
        # /api/public/otel/v1/traces endpoint).
        tracing_enabled=_export_enabled,
    )
    _initialised = True
    log.info(
        "langfuse.initialised",
        host=settings.langfuse_host,
        environment=settings.app_env,
        export_enabled=_export_enabled,
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
    """Force-flush pending traces. No-op when export is disabled."""
    if not _initialised or not _export_enabled:
        return
    try:
        from langfuse import get_client  # noqa: PLC0415

        get_client().flush()
        log.info("langfuse.flushed")
    except Exception as exc:  # noqa: BLE001
        log.warning("langfuse.flush_failed", error=str(exc))
