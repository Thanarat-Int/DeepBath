"""Text-to-SQL service: schema description + safe execute helpers.

The schema description is **hand-crafted** rather than introspected from the
DB. For an interview demo this is more reliable (LLM gets clear semantic
hints like "amount: negative=debit, positive=credit") than raw DDL. In a
production codebase you would auto-generate this from the Alembic models
and pass it through a small enricher.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.services.sql_safety import ValidationResult, validate

log = get_logger(__name__)

# ─── Schema description shown to the LLM ────────────────────────────────────


SCHEMA_DESCRIPTION = """\
ตาราง `customers`
    customer_id    TEXT (PK)         รหัสลูกค้า เช่น 'C0001'
    full_name      TEXT              ชื่อ-นามสกุล
    monthly_income NUMERIC           รายได้ต่อเดือน (บาท)
    risk_profile   TEXT              'conservative' | 'moderate' | 'aggressive'

ตาราง `accounts`
    account_id     TEXT (PK)         รหัสบัญชี เช่น 'A1001'
    customer_id    TEXT (FK→customers)
    account_type   TEXT              'savings' | 'checking' | 'credit'
    balance        NUMERIC           ยอดคงเหลือ (บาท)

ตาราง `transactions`
    txn_id         BIGSERIAL (PK)
    account_id     TEXT (FK→accounts)
    txn_date       DATE              วันที่ทำรายการ
    amount         NUMERIC           บวก = เงินเข้า, ลบ = เงินออก
    category       TEXT              'food' | 'transport' | 'shopping'
                                     | 'utility' | 'salary' | 'investment'
    merchant       TEXT              ร้านค้าหรือผู้รับ
    description    TEXT              รายละเอียด

ตัวอย่างคำถาม → SQL:

  Q: "เดือนที่แล้วใช้กับอาหารไปเท่าไหร่ บัญชีของ C0001"
  A: SELECT ABS(SUM(amount)) AS total
     FROM transactions t
     JOIN accounts a USING (account_id)
     WHERE a.customer_id = 'C0001'
       AND t.category = 'food'
       AND t.txn_date >= date_trunc('month', CURRENT_DATE) - INTERVAL '1 month'
       AND t.txn_date <  date_trunc('month', CURRENT_DATE);

  Q: "ยอดเงินคงเหลือทุกบัญชีของ C0001"
  A: SELECT account_id, account_type, balance
     FROM accounts
     WHERE customer_id = 'C0001';

ข้อบังคับ:
  - คืน SQL **เพียงคำสั่งเดียว** เป็น `SELECT` เท่านั้น
  - ใช้ตารางและคอลัมน์ตามชื่อด้านบนเท่านั้น
  - กำหนด `LIMIT` ทุกครั้ง (สูงสุด 100)
  - กรอง `customer_id = '{customer_id}'` เสมอเพื่อไม่ให้ข้อมูลข้ามลูกค้า
"""


# ─── Execution ──────────────────────────────────────────────────────────────


@dataclass(slots=True)
class SqlExecution:
    """Result of running a validated SQL query."""
    sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int


async def run_query(session: AsyncSession, sql: ValidationResult) -> SqlExecution:
    """Execute an already-validated SQL string against the read-only DB."""
    log.info("sql.execute", tables=sql.tables, limit=sql.applied_limit)
    res = await session.execute(text(sql.sql))
    rows = [dict(r._mapping) for r in res.all()]
    cols = list(res.keys()) if rows else []
    # Stringify Decimal/datetime so `model_dump_json` downstream is painless.
    rows = [{k: _coerce(v) for k, v in r.items()} for r in rows]
    return SqlExecution(sql=sql.sql, columns=cols, rows=rows, row_count=len(rows))


def _coerce(v: Any) -> Any:
    from datetime import date, datetime
    from decimal import Decimal

    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


# ─── Convenience: validate + execute ────────────────────────────────────────


async def safe_execute(session: AsyncSession, raw_sql: str) -> SqlExecution:
    """Validate and execute a generated SQL string in one call."""
    validated = validate(raw_sql)
    return await run_query(session, validated)
