"""SQL safety validator for the Text-to-SQL agent.

A two-layer defense:
  1. **AST validation (this file)** — parse with `sqlglot`, walk the tree,
     reject anything that is not a single read-only `SELECT` against an
     allow-listed set of tables. Also enforces a `LIMIT` to keep result
     sets bounded.
  2. **Database role** — the agent connects as `deepbaht_ro` which has only
     SELECT privileges. Even if an exploit slips past layer 1, Postgres
     itself rejects writes (see `data/seed/04-readonly-role.sql`).

This module is **pure**: no I/O, no network — fully unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass

import sqlglot
from sqlglot import exp

# ── Configuration ───────────────────────────────────────────────────────────

ALLOWED_TABLES: frozenset[str] = frozenset({"customers", "accounts", "transactions"})
"""Tables the SQL agent is allowed to query. Extend explicitly when you add
new tables — never wildcard. Keeps the attack surface small."""

MAX_LIMIT: int = 100
"""Hard cap on `LIMIT`. Even if the LLM emits a higher one we clamp it."""

DEFAULT_LIMIT: int = 25
"""Applied when the LLM forgets to include a `LIMIT` clause."""


# ── Result type ─────────────────────────────────────────────────────────────


@dataclass(slots=True)
class ValidationResult:
    """Outcome of validating + sanitising a generated SQL string."""

    sql: str               # the safe-to-execute SQL (may differ from input)
    tables: list[str]      # tables referenced (lowercased)
    applied_limit: int     # the LIMIT that ended up on the query

    def __str__(self) -> str:
        return self.sql


class UnsafeSQLError(ValueError):
    """Raised when a generated query violates safety policy."""


# ── Validator ───────────────────────────────────────────────────────────────


def validate(sql: str) -> ValidationResult:
    """Parse, validate, and sanitise a SQL string.

    Raises `UnsafeSQLError` on any policy violation; returns a safe variant
    (with `LIMIT` enforced) on success.
    """
    sql = sql.strip().rstrip(";")
    if not sql:
        raise UnsafeSQLError("empty query")

    # ── Parse ────────────────────────────────────────────────────────────────
    try:
        statements = sqlglot.parse(sql, read="postgres")
    except Exception as exc:  # noqa: BLE001 — surface parser msg directly
        raise UnsafeSQLError(f"invalid SQL: {exc}") from exc

    if len(statements) != 1 or statements[0] is None:
        raise UnsafeSQLError("only a single statement is allowed")

    tree = statements[0]

    # ── Top-level must be SELECT (or a UNION of SELECTs) ─────────────────────
    if not isinstance(tree, (exp.Select, exp.Union)):
        raise UnsafeSQLError(
            f"only SELECT queries are permitted; got {type(tree).__name__}"
        )

    # ── Forbid any DML/DDL/system-tweaks anywhere in the tree ────────────────
    # Note: sqlglot >=25 renamed `AlterTable` → `Alter` (covers all ALTER
    # variants). Keep the list explicit so reviewers can audit at a glance.
    for node in tree.walk():
        if isinstance(
            node,
            (
                exp.Insert,
                exp.Update,
                exp.Delete,
                exp.Drop,
                exp.Alter,
                exp.Create,
                exp.TruncateTable,
                exp.Merge,
                exp.Command,         # raw passthrough commands like SET, COPY
            ),
        ):
            raise UnsafeSQLError(f"forbidden statement type: {type(node).__name__}")

    # ── Allow-list referenced tables ─────────────────────────────────────────
    referenced: set[str] = set()
    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        if name not in ALLOWED_TABLES:
            raise UnsafeSQLError(f"table '{name}' is not in the allow-list")
        referenced.add(name)

    if not referenced:
        raise UnsafeSQLError("query references no known table")

    # ── Reject information_schema / pg_catalog access via column refs ────────
    for ident in tree.find_all(exp.Identifier):
        if ident.name.lower() in {"information_schema", "pg_catalog"}:
            raise UnsafeSQLError("system catalog access is forbidden")

    # ── Enforce LIMIT (clamp / inject) ───────────────────────────────────────
    applied_limit = _enforce_limit(tree)

    safe_sql = tree.sql(dialect="postgres")
    return ValidationResult(
        sql=safe_sql,
        tables=sorted(referenced),
        applied_limit=applied_limit,
    )


def _enforce_limit(tree: exp.Expression) -> int:
    """Mutate the parse tree so the final query has a sane LIMIT.

    - Missing LIMIT → inject DEFAULT_LIMIT.
    - LIMIT > MAX_LIMIT or non-numeric → clamp to MAX_LIMIT.
    """
    limit_node: exp.Limit | None = tree.args.get("limit")
    if limit_node is None:
        tree.set("limit", exp.Limit(expression=exp.Literal.number(DEFAULT_LIMIT)))
        return DEFAULT_LIMIT

    raw = limit_node.expression
    try:
        n = int(raw.name) if isinstance(raw, exp.Literal) else MAX_LIMIT
    except ValueError:
        n = MAX_LIMIT
    n = min(max(n, 1), MAX_LIMIT)
    limit_node.set("expression", exp.Literal.number(n))
    return n
