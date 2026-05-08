"""POST /chat — main entry point that delegates to the LangGraph supervisor.

Day 1: returns a placeholder response so the API contract is testable end-to-end.
Day 1 (later): wired up to the LangGraph supervisor in `app.agents.supervisor`.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.agents.supervisor import run_supervisor
from app.core.logging import get_logger
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])
log = get_logger(__name__)


@router.post("", response_model=ChatResponse, summary="Multi-agent chat turn")
async def chat(request: ChatRequest) -> ChatResponse:
    """Run the user's message through the LangGraph supervisor and return the
    final answer plus a trace of which agents contributed.
    """
    log.info("chat.request", session_id=request.session_id, msg_len=len(request.message))

    try:
        result = await run_supervisor(
            session_id=request.session_id,
            message=request.message,
            history=request.history,
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("chat.error", session_id=request.session_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent execution failed.",
        ) from exc

    log.info(
        "chat.response",
        session_id=request.session_id,
        agent_path=result.agent_path,
        answer_len=len(result.answer),
    )
    return result
