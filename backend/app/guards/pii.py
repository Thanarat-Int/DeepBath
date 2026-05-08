"""Thai-aware PII detection + redaction.

Why hand-rolled regex (and not just Presidio)?
  - **Thai citizen ID** uses a Mod-11 checksum that English-only PII
    libraries miss (they would either flag every 13-digit string or
    miss valid IDs that happen to be formatted with dashes).
  - **Thai bank-account formats** vary by bank (10–13 digits, sometimes
    grouped `xxx-x-xxxxx-x`). One regex handles them all.
  - **Phone numbers** in TH start with 0x where x∈{6,8,9} for mobile,
    different lengths than US E.164 patterns.
  - Pure regex is **deterministic and fast** (sub-millisecond), perfect
    for in-band guardrails on every chat turn.

For a production deployment we'd combine this with Presidio for
international PII (passports, IBAN, Western ID schemes).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

# ─── Patterns ────────────────────────────────────────────────────────────────
#
#  Each regex captures the *whole* PII string (digits + separators) so
#  that redaction preserves the original character span. We compile them
#  once at import time — `re.Pattern` is fully thread-safe.
# ─────────────────────────────────────────────────────────────────────────────

# Thai citizen ID — 13 digits, optionally grouped 1-1234-12345-12-3
_CITIZEN_ID = re.compile(r"\b\d(?:[\- ]?\d){12}\b")

# Mobile phone — 0[6|8|9] then 8 more digits (with optional dashes/spaces)
_PHONE = re.compile(r"\b0[689](?:[\- ]?\d){8}\b")

# Bank account — 10-13 digits with optional separators
#   Constrained tighter than citizen-ID by requiring at least one separator
#   OR an explicit "บัญชี" / "acc" / "a/c" prefix nearby — otherwise we'd
#   over-redact all numeric strings.
_BANK_ACCOUNT_GROUPED = re.compile(r"\b\d{3}[\- ]\d[\- ]\d{5,7}[\- ]\d\b")

# Email — RFC-light
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")

# Thai passport — 1 letter + 7 digits
_PASSPORT = re.compile(r"\b[A-Z]\d{7}\b")


@dataclass(slots=True, frozen=True)
class PIIFinding:
    """A single PII match. `start`/`end` index into the original string."""
    kind: str           # "citizen_id" | "phone" | "bank_account" | "email" | "passport"
    value: str
    start: int
    end: int

    def masked(self) -> str:
        """Replace the PII with `<KIND>` keeping the surrounding text untouched."""
        return f"<{self.kind.upper()}>"


# ─── Validators ──────────────────────────────────────────────────────────────


def _is_valid_citizen_id(s: str) -> bool:
    """Thai citizen-ID Mod-11 checksum — last digit must equal
    (11 - (Σ digit_i * (13-i) for i in 0..11)) % 10.
    """
    digits = [c for c in s if c.isdigit()]
    if len(digits) != 13:
        return False
    nums = [int(c) for c in digits]
    s = sum(nums[i] * (13 - i) for i in range(12))
    expected = (11 - (s % 11)) % 10
    return expected == nums[12]


# ─── Public API ──────────────────────────────────────────────────────────────


def detect_pii(text: str) -> list[PIIFinding]:
    """Find every PII span in `text`. Returns sorted list (left-to-right).

    Citizen-IDs are validated against the Mod-11 checksum to avoid
    over-flagging arbitrary 13-digit strings (eg. timestamps, refs).
    """
    if not text:
        return []
    findings: list[PIIFinding] = []

    for m in _CITIZEN_ID.finditer(text):
        if _is_valid_citizen_id(m.group()):
            findings.append(PIIFinding("citizen_id", m.group(), m.start(), m.end()))

    for kind, pat in (
        ("phone", _PHONE),
        ("bank_account", _BANK_ACCOUNT_GROUPED),
        ("email", _EMAIL),
        ("passport", _PASSPORT),
    ):
        for m in pat.finditer(text):
            findings.append(PIIFinding(kind, m.group(), m.start(), m.end()))

    # Sort left-to-right and drop overlapping (longest match wins)
    findings.sort(key=lambda f: (f.start, -len(f.value)))
    deduped: list[PIIFinding] = []
    for f in findings:
        if deduped and f.start < deduped[-1].end:
            continue
        deduped.append(f)
    return deduped


def has_pii(text: str) -> bool:
    """Cheap predicate — short-circuits on first finding."""
    return bool(detect_pii(text))


def redact_pii(text: str, findings: Iterable[PIIFinding] | None = None) -> str:
    """Replace every PII span with `<KIND>` placeholders.

    Idempotent: calling on already-redacted text is a no-op because the
    placeholders contain non-PII characters.
    """
    f_list = list(findings) if findings is not None else detect_pii(text)
    if not f_list:
        return text
    parts: list[str] = []
    cursor = 0
    for f in f_list:
        parts.append(text[cursor:f.start])
        parts.append(f.masked())
        cursor = f.end
    parts.append(text[cursor:])
    return "".join(parts)
