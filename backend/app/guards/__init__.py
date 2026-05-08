"""Guardrails layer — input/output safety checks.

Banking GenAI has two non-negotiable safety surfaces:

  1. **PII** — never echo (or trace, or log) a customer's citizen ID,
     bank account, phone, or email back to anyone, including the LLM.
  2. **Prompt-injection / jailbreak** — refuse obvious "ignore your
     instructions" attempts before they hit the model.

This module ships **focused Thai-aware heuristics** — fast, deterministic,
unit-tested. For a production deployment you would layer these on top of
LLM-based safety classifiers (Llama Guard, Constitutional AI, Guardrails
AI hub validators) which are slower but catch more sophisticated attacks.
"""

from app.guards.jailbreak import contains_jailbreak_attempt
from app.guards.pii import (
    PIIFinding,
    detect_pii,
    has_pii,
    redact_pii,
)

__all__ = [
    "PIIFinding",
    "contains_jailbreak_attempt",
    "detect_pii",
    "has_pii",
    "redact_pii",
]
