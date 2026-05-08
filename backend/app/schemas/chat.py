"""Chat API request / response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["user", "assistant", "system", "tool"]
AgentName = Literal["supervisor", "rag", "sql", "mcp", "advisor"]


class ChatMessage(BaseModel):
    """A single turn in the conversation."""
    role: Role
    content: str
    agent: AgentName | None = None


class ChatRequest(BaseModel):
    """Inbound chat request from the frontend."""
    session_id: str = Field(..., description="Stable session identifier for memory + tracing")
    message: str = Field(..., min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list)


class AgentTrace(BaseModel):
    """Per-node trace entry — used by the UI to visualise the agent graph."""
    agent: AgentName
    input: str
    output: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0


class ChatResponse(BaseModel):
    """Outbound chat response."""
    session_id: str
    answer: str
    agent_path: list[AgentName] = Field(default_factory=list, description="Order of agents that handled the request")
    traces: list[AgentTrace] = Field(default_factory=list)
    finished_at: datetime = Field(default_factory=datetime.utcnow)
