"""
Safety guardrails & input filtering for the SiteSense agent.

Scans prompts and untrusted inputs for prompt injection patterns,
system overrides, and destructive shell/SQL commands.
"""

import re
from typing import Tuple

# Regex signatures for prompt injection, jailbreaks, and role override attempts
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

# Sensitive command keywords that should never be sent in user prompts
UNSAFE_WORDS = [
    "sudo", "rm -rf", "delete from", "drop table", "alter user", "truncate table"
]


def check_input_guardrail(text: str) -> Tuple[bool, str]:
    """
    Validates user input before sending to the LLM.
    Returns (is_safe, reason).
    """
    if not text or not text.strip():
        return True, "Valid input."

    normalized = text.lower()

    # Check for known injection signatures
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, normalized):
            return False, f"Blocked: Malicious prompt injection pattern detected ('{pattern}')."

    # Block destructive shell and SQL keywords
    for keyword in UNSAFE_WORDS:
        if keyword in normalized:
            return False, f"Blocked: Potentially dangerous command keyword detected ('{keyword}')."

    return True, "Input passed safety guardrails."


def sanitize_untrusted_content(untrusted_text: str) -> str:
    """
    Cleans up raw OCR / scanned document text before feeding into prompts,
    neutralizing any stray prompt tokens or code block markers.
    """
    if not untrusted_text:
        return ""
    
    # Neutralize role marker spoofing
    cleaned = re.sub(r"(\bSystem\b|\bAssistant\b|\bUser\b):", r"[\1]:", untrusted_text, flags=re.IGNORECASE)
    # Strip markdown code fencing markers to prevent escaping context
    cleaned = re.sub(r"```[a-z]*\s*", "", cleaned)
    return cleaned
