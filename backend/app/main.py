"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.monitoring.langfuse_client import flush as langfuse_flush
from app.monitoring.langfuse_client import init_langfuse
from app.routers import chat, health

configure_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Run startup / shutdown side-effects.

    - **Startup**: initialise the Langfuse global client so the callback
      handler is ready before the first /chat request.
    - **Shutdown**: flush pending Langfuse spans so we don't lose the last
      few traces when the container is recreated.
    """
    log.info("app.startup", version=__version__)
    init_langfuse()
    try:
        yield
    finally:
        langfuse_flush()
        log.info("app.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Multi-agent banking assistant — Typhoon LLM + LangGraph + MCP.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(chat.router)

    return app


app = create_app()
