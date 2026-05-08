"""POST /chat — main entry point that delegates to the LangGraph supervisor.

Request flow
────────────
   client → /chat → [Guardrails: jailbreak + PII redact]
                  → LangGraph supervisor (multi-agent)
                  → [Guardrails: PII scan on output]
                  → response

Why redact PII *before* the LLM sees it?
  Even though we self-host nothing of the user's data on Typhoon's side,
  defence-in-depth says: never send a citizen-ID or bank-account number
  to a third-party API. Our redactor swaps them for `<CITIZEN_ID>` /
  `<BANK_ACCOUNT>` placeholders before the supervisor runs — the model
  still understands the question, the wire never carries the secret.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.agents.supervisor import run_supervisor
from app.core.logging import get_logger
from app.guards import (
    contains_jailbreak_attempt,
    detect_pii,
    redact_pii,
)
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])
log = get_logger(__name__)


REFUSAL_MESSAGE = (
    "ขออภัย คำขอของท่านดูเหมือนจะพยายามเปลี่ยนแปลงคำสั่งของระบบ "
    "ระบบไม่สามารถดำเนินการให้ได้ กรุณาถามใหม่ในเชิงการเงิน/ธุรกรรมตามปกติ"
)


@router.post("", response_model=ChatResponse, summary="Multi-agent chat turn")
async def chat(request: ChatRequest) -> ChatResponse:
    """Run the user's message through guardrails → LangGraph supervisor."""

    # ── Pre-flight guard 1: jailbreak detection ─────────────────────────────
    if contains_jailbreak_attempt(request.message):
        log.warning(
            "chat.jailbreak_detected",
            session_id=request.session_id,
            preview=request.message[:80],
        )
        return ChatResponse(
            session_id=request.session_id,
            answer=REFUSAL_MESSAGE,
            agent_path=[],
            traces=[],
        )

    # ── Pre-flight guard 2: redact PII before the model sees it ─────────────
    pii_findings = detect_pii(request.message)
    if pii_findings:
        log.info(
            "chat.pii_redacted",
            session_id=request.session_id,
            kinds=[f.kind for f in pii_findings],
            count=len(pii_findings),
        )
    safe_message = redact_pii(request.message, pii_findings)

    log.info(
        "chat.request",
        session_id=request.session_id,
        msg_len=len(safe_message),
        pii_redacted=len(pii_findings),
    )

    # ── Hand off to LangGraph ───────────────────────────────────────────────
    try:
        result = await run_supervisor(
            session_id=request.session_id,
            message=safe_message,
            history=request.history,
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("chat.error", session_id=request.session_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent execution failed.",
        ) from exc

    # ── Post-flight guard: never echo PII back ─────────────────────────────
    out_findings = detect_pii(result.answer)
    if out_findings:
        log.warning(
            "chat.output_pii_redacted",
            session_id=request.session_id,
            kinds=[f.kind for f in out_findings],
        )
        result.answer = redact_pii(result.answer, out_findings)

    log.info(
        "chat.response",
        session_id=request.session_id,
        agent_path=result.agent_path,
        answer_len=len(result.answer),
    )
    return result
