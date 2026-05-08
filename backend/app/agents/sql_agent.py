"""Text-to-SQL agent — translate Thai questions about transactions/accounts
into safe SQL, execute it on the read-only DB, then narrate the result.

Three-step pipeline (visible to LangFuse as nested spans on Day 2):

    user question ──▶ (1) Typhoon → SQL string
                  ──▶ (2) sqlglot validator + RO Postgres execute
                  ──▶ (3) Typhoon → friendly Thai answer + show SQL

The SQL is **shown back to the user** in the answer block so reviewers can
verify what was queried — this is a deliberate trust signal in regulated
domains. (Production might gate this behind a "/explain" toggle.)
"""

from __future__ import annotations

import json
import time

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.core.config import get_settings
from app.core.db import get_session_factory_ro
from app.core.llm import get_llm
from app.core.logging import get_logger
from app.schemas.chat import AgentTrace
from app.services.sql_safety import UnsafeSQLError, validate
from app.services.sql_service import SCHEMA_DESCRIPTION, SqlExecution, run_query

log = get_logger(__name__)


# ─── Step 1: NL → SQL ────────────────────────────────────────────────────────


GEN_SQL_SYSTEM = """คุณคือ Text-to-SQL agent ของระบบธนาคาร SCB
หน้าที่ของคุณคือแปลคำถามของลูกค้าเป็น **PostgreSQL SELECT statement** เดียว
ตาม schema และข้อบังคับด้านล่าง คืนค่ากลับเป็น JSON ตาม schema เท่านั้น
อย่ามี markdown code-fence หรือคำอธิบายเพิ่มเติม
"""


def _gen_sql_user(question: str, customer_id: str) -> str:
    return (
        f"{SCHEMA_DESCRIPTION.replace('{customer_id}', customer_id)}\n\n"
        f"คำถามลูกค้า (customer_id ปัจจุบัน = '{customer_id}'): {question}\n\n"
        'ตอบในรูปแบบ {"sql": "<query>", "rationale": "<หนึ่งบรรทัดอธิบาย>"}'
    )


async def _generate_sql(question: str, customer_id: str) -> tuple[str, str]:
    """Ask Typhoon to write the SQL. Returns (sql, rationale)."""
    llm = get_llm("fast")
    response = await llm.ainvoke(
        [
            SystemMessage(content=GEN_SQL_SYSTEM),
            HumanMessage(content=_gen_sql_user(question, customer_id)),
        ]
    )
    raw = str(response.content).strip()
    # The model should emit pure JSON; tolerate stray code fences just in case.
    raw = raw.strip("`")
    if raw.startswith("json\n"):
        raw = raw[5:]
    try:
        payload = json.loads(raw)
        return str(payload["sql"]), str(payload.get("rationale", ""))
    except (json.JSONDecodeError, KeyError) as exc:
        raise UnsafeSQLError(f"LLM returned non-JSON output: {raw[:200]}") from exc


# ─── Step 3: result → Thai narrative ─────────────────────────────────────────


SUMMARIZE_SYSTEM = """คุณคือผู้ช่วยที่อธิบายผลลัพธ์ SQL เป็นภาษาไทย กระชับ ชัดเจน
- ใช้ตัวเลขจาก JSON ที่ได้รับเท่านั้น ห้ามแต่งเติม
- หากผลลัพธ์ว่าง ให้บอกว่าไม่พบข้อมูล
- จบด้วยบรรทัด `\\n\\n_(ใช้ SQL: ...)_` แสดงคำสั่งที่รัน
- ห้ามตอบเกิน 4 ประโยค
"""


def _summarize_user(question: str, exec_result: SqlExecution) -> str:
    sample = exec_result.rows[:10]
    return (
        f"คำถาม: {question}\n"
        f"SQL ที่รัน: {exec_result.sql}\n"
        f"จำนวนแถว: {exec_result.row_count}\n"
        f"ผลลัพธ์ (สูงสุด 10 แถวแรก): {json.dumps(sample, ensure_ascii=False)}"
    )


async def _summarize(question: str, exec_result: SqlExecution) -> str:
    llm = get_llm("chat")
    response = await llm.ainvoke(
        [
            SystemMessage(content=SUMMARIZE_SYSTEM),
            HumanMessage(content=_summarize_user(question, exec_result)),
        ]
    )
    return str(response.content).strip()


# ─── LangGraph node ──────────────────────────────────────────────────────────


async def sql_node(state: AgentState) -> dict:
    question = state["user_message"]
    customer_id = get_settings().demo_customer_id
    t0 = time.perf_counter()

    # ── (1) generate ────────────────────────────────────────────────────────
    try:
        raw_sql, rationale = await _generate_sql(question, customer_id)
    except UnsafeSQLError as exc:
        return _error_trace(question, t0, f"LLM ไม่สามารถสร้าง SQL ที่อ่านได้: {exc}")

    # ── (2) validate + execute ──────────────────────────────────────────────
    try:
        validated = validate(raw_sql)
    except UnsafeSQLError as exc:
        log.warning("sql.unsafe", sql=raw_sql, reason=str(exc))
        return _error_trace(
            question,
            t0,
            f"ขออภัย คำถามนี้ทำให้ระบบสร้าง SQL ที่ไม่ปลอดภัย ({exc}) "
            "กรุณาถามใหม่ในรูปแบบที่จำกัดขอบเขตข้อมูลให้ชัดเจน",
        )

    factory = get_session_factory_ro()
    async with factory() as session:
        try:
            exec_result = await run_query(session, validated)
        except Exception as exc:  # noqa: BLE001
            log.exception("sql.execute_failed", sql=validated.sql)
            return _error_trace(question, t0, f"การรัน SQL ล้มเหลว: {exc}")

    # ── (3) summarise ───────────────────────────────────────────────────────
    answer = await _summarize(question, exec_result)
    latency = int((time.perf_counter() - t0) * 1000)

    log.info(
        "sql.ok",
        rationale=rationale,
        rows=exec_result.row_count,
        tables=validated.tables,
        latency_ms=latency,
    )
    trace = AgentTrace(
        agent="sql",
        input=question,
        output=f"{validated.sql}  ⇒  {exec_result.row_count} rows",
        latency_ms=latency,
    )
    return {"sql_result": answer, "agent_path": ["sql"], "traces": [trace]}


def _error_trace(question: str, t0: float, message: str) -> dict:
    return {
        "sql_result": message,
        "agent_path": ["sql"],
        "traces": [
            AgentTrace(
                agent="sql",
                input=question,
                output=message,
                latency_ms=int((time.perf_counter() - t0) * 1000),
            )
        ],
    }
