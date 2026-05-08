"""MCP agent — picks a banking tool from the user's intent and invokes it
through the streamable-HTTP MCP server.

Pipeline (each step shows up as a child span in Langfuse on Day 2)

    user message ──▶ (1) Typhoon → ToolCall {tool, arguments, rationale}
                 ──▶ (2) MCP client → call_tool(...)
                 ──▶ (3) Compose Thai narrative + show tool call for trust

We deliberately use a `PydanticOutputParser` (rather than LangChain's
tool-calling wrapper) because Typhoon's OpenAI-compatible API doesn't
reliably honour the function-calling protocol — same robustness story
as the supervisor.
"""

from __future__ import annotations

import time
from typing import Any, Literal

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.agents.state import AgentState
from app.core.config import get_settings
from app.core.llm import get_llm
from app.core.logging import get_logger
from app.schemas.chat import AgentTrace
from app.services import mcp_client

log = get_logger(__name__)


# ─── ToolCall schema ─────────────────────────────────────────────────────────


class ToolCall(BaseModel):
    """The MCP tool the LLM has decided to invoke for this user turn."""

    tool: Literal[
        "get_balance",
        "get_recent_transactions",
        "transfer",
        "get_market_quote",
        "get_fx_rate",
    ] = Field(..., description="The MCP tool name to call.")
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON object matching the chosen tool's input schema.",
    )
    rationale: str = Field(..., description="One-sentence explanation in Thai.")


_parser = PydanticOutputParser(pydantic_object=ToolCall)


# ─── Prompt ──────────────────────────────────────────────────────────────────


SYSTEM_PROMPT = (
    "คุณคือ MCP agent ของ DeepBaht ระบบผู้ช่วยทางการเงินส่วนบุคคล\n"
    "คุณมีเครื่องมือ (tools) ดังนี้:\n"
    "  1. get_balance(account_id: str)\n"
    "       เช็คยอดคงเหลือของบัญชี\n"
    "  2. get_recent_transactions(account_id: str, limit: int = 5)\n"
    "       ดูธุรกรรมล่าสุด\n"
    "  3. transfer(from_account: str, to_account: str, amount: float, memo: str = '')\n"
    "       โอนเงิน (mock - ไม่ได้โอนจริง)\n"
    "  4. get_market_quote(symbol: str)\n"
    "       ดูราคาหุ้นบน SET\n"
    "  5. get_fx_rate(base: str, quote: str)\n"
    "       อัตราแลกเปลี่ยน เช่น base='THB' quote='USD'\n\n"
    "บริบทลูกค้าปัจจุบัน:\n"
    "  - customer_id = '{customer_id}'\n"
    "  - บัญชีหลัก (default 'from_account') = 'A1002'\n\n"
    "เลือก tool 1 ตัวที่เหมาะสมที่สุด แล้วสกัด arguments จากคำถามของลูกค้า\n"
    "หากคำถามไม่ระบุ from_account ในการโอน ให้ใช้บัญชีหลัก\n\n"
    "ตอบกลับเป็น JSON ตาม schema ด้านล่างเท่านั้น ห้ามใส่ markdown หรือ code-fence\n\n"
    "{format_instructions}"
)


PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "คำถามลูกค้า: {message}"),
    ]
).partial(format_instructions=_parser.get_format_instructions())


# ─── Node ────────────────────────────────────────────────────────────────────


async def mcp_node(state: AgentState) -> dict:
    """LangGraph node: pick tool → call MCP → format reply."""
    question = state["user_message"]
    customer_id = get_settings().demo_customer_id
    t0 = time.perf_counter()

    # ── (1) Pick tool ───────────────────────────────────────────────────────
    llm = get_llm("fast")
    chain = PROMPT.partial(customer_id=customer_id) | llm | _parser
    try:
        decision: ToolCall = await chain.ainvoke({"message": question})
    except Exception as exc:  # noqa: BLE001
        return _fail(question, t0, f"เลือก tool ไม่สำเร็จ: {exc}")

    log.info("mcp.tool_picked", tool=decision.tool, args=decision.arguments)

    # ── (2) Invoke MCP ──────────────────────────────────────────────────────
    try:
        result = await mcp_client.call_tool(decision.tool, decision.arguments)
    except Exception as exc:  # noqa: BLE001
        log.exception("mcp.call_failed", tool=decision.tool)
        return _fail(question, t0, f"การเรียก MCP tool ล้มเหลว: {exc}")

    # ── (3) Compose user-facing answer ──────────────────────────────────────
    answer = (
        f"{result}\n\n"
        f"_เลือกใช้ tool `{decision.tool}({_fmt_args(decision.arguments)})` "
        f"— {decision.rationale}_"
    )

    latency = int((time.perf_counter() - t0) * 1000)
    trace = AgentTrace(
        agent="mcp",
        input=question,
        output=f"{decision.tool}({decision.arguments}) → {result[:80]}",
        latency_ms=latency,
    )
    return {"mcp_result": answer, "agent_path": ["mcp"], "traces": [trace]}


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _fmt_args(args: dict[str, Any]) -> str:
    return ", ".join(f"{k}={v!r}" for k, v in args.items())


def _fail(question: str, t0: float, message: str) -> dict:
    return {
        "mcp_result": message,
        "agent_path": ["mcp"],
        "traces": [
            AgentTrace(
                agent="mcp",
                input=question,
                output=message,
                latency_ms=int((time.perf_counter() - t0) * 1000),
            )
        ],
    }
