"""LangGraph shared state.

`AgentState` is the single source of truth that flows through every node in
the graph. Each agent reads from it (e.g. `messages`, `route`) and appends
its trace + partial output. The supervisor uses `route` to decide the next
node; LangGraph automatically merges updates back into state.
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import BaseMessage

from app.schemas.chat import AgentTrace

Route = Literal["rag", "sql", "mcp", "advisor", "finalize", "end"]


class AgentState(TypedDict, total=False):
    """Shared state passed between LangGraph nodes."""

    # ── Inputs ──────────────────────────────────────────────────────────────
    session_id: str
    user_message: str

    # ── Conversation memory ─────────────────────────────────────────────────
    # `Annotated[..., operator.add]` tells LangGraph to *append* updates from
    # parallel nodes instead of overwriting — critical for fan-out fan-in flows.
    messages: Annotated[list[BaseMessage], operator.add]

    # ── Routing ─────────────────────────────────────────────────────────────
    route: Route               # next agent to invoke
    agent_path: Annotated[list[str], operator.add]   # agents visited so far
    iteration: int             # safeguard against infinite loops

    # ── Agent outputs (any agent may write its slice) ───────────────────────
    rag_context: str | None
    sql_result: str | None
    mcp_result: str | None
    advisor_notes: str | None

    # ── Final ───────────────────────────────────────────────────────────────
    final_answer: str | None
    traces: Annotated[list[AgentTrace], operator.add]
