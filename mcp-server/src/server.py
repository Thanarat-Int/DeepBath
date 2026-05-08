"""Banking MCP server — mock implementations of common banking actions.

The Model Context Protocol (MCP) lets any MCP-compatible LLM client (Claude
Desktop, our LangGraph agent, Cursor, etc.) discover and call these tools
through a single standard interface.

Tools exposed (mocked for the demo — no real money is moved):
  - get_balance(account_id)
  - get_recent_transactions(account_id, limit)
  - transfer(from_account, to_account, amount, memo)
  - get_market_quote(symbol)
  - get_fx_rate(base, quote)

Day-1 ships placeholders. Day-2 wires them to the same Postgres used by the
SQL agent so transfers update real seed data.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool

# ──────────────────────────────────────────────────────────────────────────────

server: Server = Server("autox-banking-mcp")


# ─── Tool: get_balance ────────────────────────────────────────────────────────


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_balance",
            description="Return the current available balance for a given account_id.",
            inputSchema={
                "type": "object",
                "properties": {"account_id": {"type": "string"}},
                "required": ["account_id"],
            },
        ),
        Tool(
            name="get_recent_transactions",
            description="Return up to `limit` most recent transactions for an account.",
            inputSchema={
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                },
                "required": ["account_id"],
            },
        ),
        Tool(
            name="transfer",
            description=(
                "Transfer THB between two accounts. Returns a transaction reference. "
                "All transfers are MOCK in the demo environment."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "from_account": {"type": "string"},
                    "to_account": {"type": "string"},
                    "amount": {"type": "number", "minimum": 1},
                    "memo": {"type": "string"},
                },
                "required": ["from_account", "to_account", "amount"],
            },
        ),
        Tool(
            name="get_market_quote",
            description="Fetch a (mock) latest market quote for a stock symbol on SET.",
            inputSchema={
                "type": "object",
                "properties": {"symbol": {"type": "string"}},
                "required": ["symbol"],
            },
        ),
        Tool(
            name="get_fx_rate",
            description="Fetch the (mock) FX rate from `base` to `quote` (e.g. THB→USD).",
            inputSchema={
                "type": "object",
                "properties": {
                    "base": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": ["base", "quote"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[dict[str, str]]:
    """Dispatch tool call. Returns MCP content blocks (text)."""
    if name == "get_balance":
        return _ok(f"Account {arguments['account_id']} available balance: 125,430.50 THB")

    if name == "get_recent_transactions":
        limit = int(arguments.get("limit", 5))
        rows = [
            f"{(datetime.utcnow() - timedelta(days=i)).date()} · -250.00 THB · ร้านอาหาร"
            for i in range(limit)
        ]
        return _ok("Recent transactions:\n" + "\n".join(rows))

    if name == "transfer":
        ref = f"TX{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        return _ok(
            f"Transferred {arguments['amount']} THB "
            f"from {arguments['from_account']} → {arguments['to_account']}. "
            f"Ref: {ref}  (MOCK)"
        )

    if name == "get_market_quote":
        sym = arguments["symbol"].upper()
        return _ok(f"{sym}: 142.50 THB (+1.43%)  (MOCK)")

    if name == "get_fx_rate":
        return _ok(f"1 {arguments['base']} = 0.0287 {arguments['quote']}  (MOCK)")

    return _ok(f"Unknown tool: {name}")


def _ok(text: str) -> list[dict[str, str]]:
    return [{"type": "text", "text": text}]


# ─── Entrypoint ───────────────────────────────────────────────────────────────


async def main() -> None:
    """Run the MCP server.

    Day-1: stdio transport (works with `mcp dev` and Claude Desktop).
    Day-2: switch to streamable-HTTP so the FastAPI backend can connect over
    `MCP_SERVER_URL`.
    """
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())
    else:
        # Placeholder for the HTTP transport switch on Day 2.
        raise NotImplementedError(f"Transport '{transport}' not wired yet.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
