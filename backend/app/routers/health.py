"""Liveness / readiness endpoints — used by Docker healthcheck and CI."""

from __future__ import annotations

from fastapi import APIRouter

from app import __version__

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict:
    return {"status": "ok", "version": __version__}


@router.get("/ready", summary="Readiness probe")
async def ready() -> dict:
    """Extended in Day 2 to verify Typhoon, Postgres, MCP, LangFuse connectivity."""
    return {"status": "ready", "checks": {"app": "ok"}}
