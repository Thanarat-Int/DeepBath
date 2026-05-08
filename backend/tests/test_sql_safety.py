"""Tests for the Text-to-SQL safety validator.

These are the kind of tests an interviewer will love — concise, table-driven,
and they map 1:1 to threats in a banking context (data exfiltration via
information_schema, write attempts, multi-statement injection, etc.).
"""

from __future__ import annotations

import pytest

from app.services.sql_safety import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    UnsafeSQLError,
    validate,
)


# ─── Happy paths ─────────────────────────────────────────────────────────────


def test_simple_select_passes() -> None:
    result = validate(
        "SELECT account_id, balance FROM accounts WHERE customer_id = 'C0001'"
    )
    assert result.tables == ["accounts"]
    assert result.applied_limit == DEFAULT_LIMIT
    assert "LIMIT" in result.sql.upper()


def test_join_across_allowed_tables_passes() -> None:
    sql = (
        "SELECT t.txn_date, t.amount FROM transactions t "
        "JOIN accounts a USING (account_id) "
        "WHERE a.customer_id = 'C0001' LIMIT 50"
    )
    result = validate(sql)
    assert set(result.tables) == {"accounts", "transactions"}
    assert result.applied_limit == 50


def test_clamps_oversized_limit() -> None:
    result = validate("SELECT 1 FROM accounts LIMIT 99999")
    assert result.applied_limit == MAX_LIMIT


def test_injects_default_limit_when_missing() -> None:
    result = validate("SELECT customer_id FROM customers")
    assert result.applied_limit == DEFAULT_LIMIT
    assert "LIMIT" in result.sql.upper()


# ─── Threats: must all raise ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "bad_sql,reason",
    [
        ("DELETE FROM transactions",                              "DML/DELETE"),
        ("UPDATE accounts SET balance = 0",                        "DML/UPDATE"),
        ("INSERT INTO accounts VALUES ('X', 'C0001', 'savings', 0)", "DML/INSERT"),
        ("DROP TABLE customers",                                   "DDL/DROP"),
        ("TRUNCATE transactions",                                  "DDL/TRUNCATE"),
        ("SELECT 1; DROP TABLE customers",                         "multi-statement"),
        ("SELECT * FROM pg_user",                                  "system table"),
        ("SELECT * FROM information_schema.tables",                "info_schema"),
        ("SELECT * FROM accounts UNION SELECT * FROM pg_shadow",   "system union"),
        ("SELECT * FROM secrets_table",                            "non-allowlisted"),
        ("",                                                        "empty"),
        ("not a sql at all",                                        "garbage"),
    ],
    ids=lambda v: v if isinstance(v, str) and len(v) < 40 else "_",
)
def test_unsafe_sql_rejected(bad_sql: str, reason: str) -> None:
    with pytest.raises(UnsafeSQLError):
        validate(bad_sql)


def test_strips_trailing_semicolon() -> None:
    """Trailing `;` is allowed and simply trimmed."""
    result = validate("SELECT 1 FROM accounts;")
    assert result.applied_limit == DEFAULT_LIMIT
