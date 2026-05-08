"""DeepBaht Banking MCP server — streamable-HTTP transport.

The Model Context Protocol (MCP) lets any MCP-compatible LLM client
(Claude Desktop, our LangGraph agent, Cursor, IDE plugins, …) discover
and invoke these tools through a single standard interface — write the
tool once, every client gets it.

Day 1 shipped a stdio-only stub. Day 2 switches to **streamable-HTTP**
so the FastAPI backend (running in another container) can talk to it
over the docker network at http://mcp-server:4765/mcp.

Tools exposed (all MOCK — no real money is moved in the demo)
  - get_balance(account_id)
  - get_recent_transactions(account_id, limit)
  - transfer(from_account, to_account, amount, memo)
  - get_market_quote(symbol)
  - get_fx_rate(base, quote)
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from mcp.server.fastmcp import FastMCP

# ── Server bootstrap ────────────────────────────────────────────────────────

mcp: FastMCP = FastMCP(
    "deepbaht-banking-mcp",
    host=os.getenv("MCP_HOST", "0.0.0.0"),
    port=int(os.getenv("MCP_PORT", "4765")),
)


# ── Tools ───────────────────────────────────────────────────────────────────


@mcp.tool()
async def get_balance(account_id: str) -> str:
    """Return the current available balance for a given account_id.

    Demo data — production would query the core-banking system.
    """
    fixtures = {
        "A1001": "125,430.50",
        "A1002": "18,200.00",
        "A2001": "840,000.00",
        "A3001": "42,500.75",
    }
    bal = fixtures.get(account_id, "0.00")
    return f"บัญชี {account_id} มียอดคงเหลือ {bal} บาท"


@mcp.tool()
async def get_recent_transactions(account_id: str, limit: int = 5) -> str:
    """Return up to `limit` most recent transactions for an account."""
    limit = max(1, min(limit, 20))
    rows = [
        f"{(datetime.utcnow() - timedelta(days=i)).date()} · -250.00 บาท · ร้านอาหาร"
        for i in range(limit)
    ]
    return f"ธุรกรรมล่าสุดของบัญชี {account_id}:\n" + "\n".join(rows)


@mcp.tool()
async def transfer(
    from_account: str,
    to_account: str,
    amount: float,
    memo: str = "",
) -> str:
    """Transfer THB between two accounts. Returns a transaction reference.

    All transfers are MOCK in the demo environment — no balance is mutated.
    """
    if amount <= 0:
        return "❌ จำนวนเงินต้องมากกว่า 0"
    ref = f"TX{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    note = f' (บันทึก: "{memo}")' if memo else ""
    return (
        f"✅ โอนเงิน {amount:,.2f} บาท จากบัญชี {from_account} → {to_account} "
        f"เรียบร้อย{note}\nหมายเลขอ้างอิง: {ref}  (MOCK)"
    )


@mcp.tool()
async def get_market_quote(symbol: str) -> str:
    """Fetch a (mock) latest market quote for a stock symbol on SET."""
    sym = symbol.upper().strip()
    return f"{sym}: 142.50 บาท (+1.43% วันนี้)  (MOCK)"


@mcp.tool()
async def get_fx_rate(base: str, quote: str) -> str:
    """Fetch the (mock) FX rate from `base` to `quote` (e.g. THB→USD)."""
    pair = f"{base.upper()}/{quote.upper()}"
    rates = {"THB/USD": "0.0287", "USD/THB": "34.85", "THB/EUR": "0.0263"}
    rate = rates.get(pair, "1.0000")
    return f"อัตราแลกเปลี่ยน {pair}: 1 {base.upper()} = {rate} {quote.upper()}  (MOCK)"


# ── Entrypoint ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # `streamable-http` exposes a Starlette app on /mcp with JSON-RPC + SSE.
    # FastMCP handles connection lifecycle, capability negotiation, and
    # tool dispatch automatically.
    mcp.run(transport="streamable-http")
