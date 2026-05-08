"""Async MCP client — calls the Banking MCP server over streamable HTTP.

The Python MCP SDK ships an async streamable-HTTP client that handles
JSON-RPC framing, SSE streaming, and capability negotiation. We wrap it
in a tiny `mcp_session()` context manager + two convenience helpers so
the rest of the backend doesn't need to know which transport we use —
swap to stdio or websocket later by replacing this file alone.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)


def _endpoint() -> str:
    """The streamable-HTTP MCP endpoint URL.

    FastMCP exposes its server at `/mcp` by default; we honour the
    `MCP_SERVER_URL` setting (which is the *base* URL, eg.
    `http://mcp-server:4765`) and append `/mcp/`.
    """
    base = get_settings().mcp_server_url.rstrip("/")
    return f"{base}/mcp/"


@asynccontextmanager
async def mcp_session():
    """Open a streamable-HTTP MCP session to the Banking MCP server.

    Yields an initialised `ClientSession`. The session is short-lived
    (one request per call) — we deliberately don't share connections
    because each /chat turn is independent and reconnect cost is low
    (<10 ms on the docker bridge network).
    """
    url = _endpoint()
    log.debug("mcp.connecting", url=url)
    async with streamablehttp_client(url) as (read, write, _close):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def call_tool(name: str, arguments: dict[str, Any]) -> str:
    """Invoke an MCP tool by name and return its concatenated text output."""
    log.info("mcp.call", tool=name, arguments=arguments)
    async with mcp_session() as session:
        result = await session.call_tool(name, arguments)
    if getattr(result, "isError", False):
        raise RuntimeError(f"MCP tool '{name}' returned an error: {result}")
    pieces: list[str] = []
    for block in result.content or []:
        text = getattr(block, "text", None)
        if text:
            pieces.append(text)
    return "\n".join(pieces) or "(no output)"


async def list_tools() -> list[dict[str, Any]]:
    """List the tools the MCP server currently exposes (for diagnostics)."""
    async with mcp_session() as session:
        result = await session.list_tools()
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.inputSchema,
        }
        for t in result.tools
    ]
