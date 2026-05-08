"""Cheap, deterministic jailbreak / prompt-injection heuristic.

This is **not** a substitute for a learned safety classifier (Llama Guard,
Constitutional AI, OpenAI moderation) — it catches the obvious 80% of
hand-written attacks and lets the system fail safe on day one. The
remaining 20% is what an LLM-based classifier earns its keep on, and is
explicitly listed in the production roadmap.

Detection strategy
──────────────────
Token-level case-insensitive substring matching on a curated phrase list
covering the well-known jailbreak vectors:
  - meta-instruction overrides ("ignore previous", "disregard above")
  - role-play hijacks ("pretend you are", "you are now DAN")
  - system-prompt extraction ("repeat your instructions", "what is your system prompt")
  - Thai-language equivalents

We treat detection as a binary signal — caller decides what to do
(refuse, redact, downgrade to safer model, log to LangFuse with a tag).
"""

from __future__ import annotations

# All comparisons are done in lowercase; keep the list lowercase too.
_PHRASES: tuple[str, ...] = (
    # Meta-instruction overrides
    "ignore previous instructions",
    "ignore prior instructions",
    "ignore the above",
    "disregard previous",
    "forget your instructions",
    "ignore your training",
    "override system prompt",
    "you are now",
    "act as if",
    "pretend to be",
    "from now on you are",
    # Role-play hijacks
    "dan mode",
    "developer mode",
    "jailbreak mode",
    "do anything now",
    # System-prompt extraction
    "what is your system prompt",
    "repeat your instructions",
    "show me your prompt",
    "print your instructions",
    "reveal your system message",
    # Thai equivalents
    "ลืมคำสั่งก่อนหน้า",
    "ละเลยคำสั่ง",
    "ตอนนี้คุณคือ",
    "แสดงคำสั่งระบบ",
    "บอก system prompt",
    "เปิดเผย prompt",
)


def contains_jailbreak_attempt(text: str) -> bool:
    """Return True if the input matches a known jailbreak phrase.

    Designed to be cheap (single pass over a small phrase list) so it
    can run on every chat turn without latency cost.
    """
    if not text:
        return False
    lowered = text.lower()
    return any(p in lowered for p in _PHRASES)
