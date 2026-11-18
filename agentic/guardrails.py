"""
SITESENSE - Guardrails & Injection Defense (Feature 4.10)
Defends against prompt injection in user queries, OCR text, and ingested documents.
Blocks unauthorized system modifications, role escalation, and data exfiltration.
"""

import re
from typing import Tuple, Dict, Any, List

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(the\s+)?system\s+prompt",
    r"you\s+are\s+now\s+dan\b",
    r"new\s+system\s+prompt:",
    r"bypass\s+(all\s+)?security",
    r"drop\s+database",
    r"system\s*:\s*override",
    r"reveal\s+(your\s+)?(system\s+prompt|secret|api[_\s]key)",
    r"print\s+environment\s+variables",
    r"jailbreak",
    r"<script\b",
    r"exec\s*\(",
    r"eval\s*\("
]

UNSAFE_WORDS = [
    "sudo", "rm -rf", "delete from", "drop table", "alter user", "truncate table"
]

def check_input_guardrail(text: str) -> Tuple[bool, str]:
    """
    Scans input text for injection patterns and jailbreak attempts.
    Returns (is_safe: bool, reason: str).
    """
    if not text or not text.strip():
        return True, "Valid input."

    lower_text = text.lower()

    # Pattern check
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lower_text):
            return False, f"Blocked: Malicious prompt injection pattern detected ('{pattern}')."

    # Destructive command strings
    for keyword in UNSAFE_WORDS:
        if keyword in lower_text:
            return False, f"Blocked: Potentially dangerous command keyword detected ('{keyword}')."

    return True, "Input passed safety guardrails."

def sanitize_untrusted_content(untrusted_text: str) -> str:
    """
    Sanitizes text extracted from OCR or scanned documents before inserting into prompt context.
    Neutralizes system-like prompts or command markers.
    """
    if not untrusted_text:
        return ""
    sanitized = re.sub(r"(\bSystem\b|\bAssistant\b|\bUser\b):", r"[\1]:", untrusted_text, flags=re.IGNORECASE)
    sanitized = re.sub(r"```[a-z]*\s*", "", sanitized)
    return sanitized

