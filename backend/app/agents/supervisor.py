"""LangGraph supervisor — routes the user query to the right specialist agent.

This is a **supervisor (router) pattern**:

      ┌─────────────┐
      │  Supervisor │  classify intent + decide route
      └──────┬──────┘
   ┌─────────┼─────────┬──────────┐
   ▼         ▼         ▼          ▼
 [RAG]    [SQL]     [MCP]     [Advisor]
   │         │         │          │
   └─────────┴─────────┴──────────┘
             ▼
      ┌─────────────┐
      │  Finalize   │  compose the final user-facing answer
      └─────────────┘

Day 1 ships the supervisor + a stub for each worker so the graph can run
end-to-end.  Each worker is fleshed out in its own file and tested in isolation:

  - `app.agents.rag_agent`        (Day 1 afternoon)
  - `app.agents.sql_agent`        (Day 1 afternoon)
  - `app.agents.mcp_agent`        (Day 2)
  - `app.agents.advisor_agent`    (Day 2)
"""

from __future__ import annotations

import time
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from app.agents.rag_agent import rag_node as _real_rag_node
from app.agents.sql_agent import sql_node as _real_sql_node
from app.agents.state import AgentState, Route
from app.core.llm import get_llm
from app.core.logging import get_logger
from app.schemas.chat import AgentTrace, ChatMessage, ChatResponse

log = get_logger(__name__)

# ─── Routing schema (structured output) ──────────────────────────────────────


class RouteDecision(BaseModel):
    """Strict schema the supervisor LLM must produce.

    We use a `PydanticOutputParser` (rather than `with_structured_output`)
    because Typhoon's OpenAI-compatible API doesn't reliably honour the
    function-calling / JSON-schema modes that LangChain's helper assumes.
    PydanticOutputParser injects an explicit JSON schema into the prompt
    and then validates the raw text reply — model-agnostic and robust.
    """

    route: Literal["rag", "sql", "mcp", "advisor"] = Field(
        ..., description="Which specialist agent should handle this turn."
    )
    reason: str = Field(..., description="One-sentence justification (Thai or English).")


_route_parser = PydanticOutputParser(pydantic_object=RouteDecision)


SUPERVISOR_SYSTEM = (
    "คุณคือ Supervisor ของ DeepBaht ระบบผู้ช่วย Multi-Agent ด้านการเงินส่วนบุคคล\n"
    "หน้าที่ของคุณคือเลือก agent ที่เหมาะสมที่สุดสำหรับคำถามของลูกค้า โดยมี 4 ทางเลือก:\n"
    "  - 'rag'      : คำถามเชิงนโยบาย ค่าธรรมเนียม เงื่อนไขผลิตภัณฑ์ (ค้นจากเอกสาร policy)\n"
    "  - 'sql'      : คำถามเกี่ยวกับธุรกรรม/ยอดเงิน/รายรับ-รายจ่ายของลูกค้า (ค้นจากฐานข้อมูล)\n"
    "  - 'mcp'      : ลูกค้าต้องการให้ทำ action เช่น โอนเงิน เช็คยอด ดูราคาหุ้น (เรียกผ่าน MCP tools)\n"
    "  - 'advisor'  : คำถามขอคำแนะนำการลงทุน/วางแผนการเงิน (ต้องใช้ reasoning + tools ผสมกัน)\n\n"
    "ตอบกลับเป็น JSON ตาม schema ด้านล่างเท่านั้น ห้ามใส่ markdown code-fence "
    "หรือคำอธิบายใดๆ นอกเหนือจาก JSON object\n\n"
    "{format_instructions}"
)


SUPERVISOR_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SUPERVISOR_SYSTEM),
        ("human", "คำถามลูกค้า: {message}"),
    ]
).partial(format_instructions=_route_parser.get_format_instructions())


# ─── Nodes ───────────────────────────────────────────────────────────────────


async def supervisor_node(state: AgentState) -> dict:
    """Classify the user's message and pick the next agent."""
    t0 = time.perf_counter()
    llm = get_llm("fast")
    chain = SUPERVISOR_PROMPT | llm | _route_parser
    try:
        decision: RouteDecision = await chain.ainvoke({"message": state["user_message"]})
    except Exception as exc:  # noqa: BLE001
        # If the model emits malformed JSON we fall back to RAG — the safest
        # default for a banking assistant ("look it up in policy").
        log.warning("supervisor.parse_failed", error=str(exc), default="rag")
        decision = RouteDecision(route="rag", reason="parse_failed_fallback")
    latency = int((time.perf_counter() - t0) * 1000)

    log.info("supervisor.route", route=decision.route, reason=decision.reason)
    trace = AgentTrace(
        agent="supervisor",
        input=state["user_message"],
        output=f"{decision.route} :: {decision.reason}",
        latency_ms=latency,
    )
    return {
        "route": decision.route,
        "agent_path": ["supervisor"],
        "traces": [trace],
        "iteration": state.get("iteration", 0) + 1,
    }


async def _stub_worker(name: Route, state: AgentState) -> dict:
    """Day-1 placeholder so the graph compiles and runs end-to-end.
    Real implementations land in their own files.
    """
    msg = f"[stub:{name}] received: {state['user_message']}"
    trace = AgentTrace(agent=name, input=state["user_message"], output=msg, latency_ms=0)  # type: ignore[arg-type]
    field = f"{name}_result" if name in {"sql", "mcp"} else (
        "rag_context" if name == "rag" else "advisor_notes"
    )
    return {field: msg, "agent_path": [name], "traces": [trace]}


async def rag_node(state: AgentState) -> dict:
    """Real RAG worker — see app.agents.rag_agent."""
    return await _real_rag_node(state)


async def sql_node(state: AgentState) -> dict:
    """Real Text-to-SQL worker — see app.agents.sql_agent."""
    return await _real_sql_node(state)


async def mcp_node(state: AgentState) -> dict:
    return await _stub_worker("mcp", state)


async def advisor_node(state: AgentState) -> dict:
    return await _stub_worker("advisor", state)


async def finalize_node(state: AgentState) -> dict:
    """Compose the customer-facing answer from whichever specialist ran."""
    raw = (
        state.get("rag_context")
        or state.get("sql_result")
        or state.get("mcp_result")
        or state.get("advisor_notes")
        or "ขออภัย ระบบยังไม่สามารถตอบคำถามนี้ได้"
    )
    # Day 1: pass-through. Day 2: rewrite with Typhoon for natural Thai phrasing
    # + Guardrails post-check.
    return {
        "final_answer": raw,
        "agent_path": ["finalize"],
        "traces": [AgentTrace(agent="supervisor", input="finalize", output=raw, latency_ms=0)],
    }


# ─── Graph wiring ────────────────────────────────────────────────────────────


def _route_selector(state: AgentState) -> str:
    """Conditional edge: supervisor → specialist."""
    return state.get("route", "rag")


def build_graph() -> StateGraph:
    """Assemble the LangGraph. Compiled once at import time."""
    g = StateGraph(AgentState)

    g.add_node("supervisor", supervisor_node)
    g.add_node("rag", rag_node)
    g.add_node("sql", sql_node)
    g.add_node("mcp", mcp_node)
    g.add_node("advisor", advisor_node)
    g.add_node("finalize", finalize_node)

    g.set_entry_point("supervisor")
    g.add_conditional_edges(
        "supervisor",
        _route_selector,
        {"rag": "rag", "sql": "sql", "mcp": "mcp", "advisor": "advisor"},
    )
    for worker in ("rag", "sql", "mcp", "advisor"):
        g.add_edge(worker, "finalize")
    g.add_edge("finalize", END)

    return g


# Compile once so we pay the LangGraph compile cost at startup, not per-request.
_compiled_graph = build_graph().compile()


# ─── Public API ──────────────────────────────────────────────────────────────


async def run_supervisor(
    session_id: str,
    message: str,
    history: list[ChatMessage],
) -> ChatResponse:
    """Run a single chat turn through the multi-agent graph."""
    initial: AgentState = {
        "session_id": session_id,
        "user_message": message,
        "messages": [HumanMessage(content=message)],
        "agent_path": [],
        "iteration": 0,
        "traces": [],
    }
    final: AgentState = await _compiled_graph.ainvoke(initial)
    return ChatResponse(
        session_id=session_id,
        answer=final.get("final_answer") or "(empty)",
        agent_path=[a for a in final.get("agent_path", []) if a in {"rag", "sql", "mcp", "advisor"}],  # type: ignore[misc]
        traces=final.get("traces", []),
    )
