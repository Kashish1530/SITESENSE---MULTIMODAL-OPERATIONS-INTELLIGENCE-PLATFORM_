"""
SITESENSE - Centralized Prompt Management & Versioning System (Feature 3.9)
Loads versioned prompt templates from dedicated repository files.
Enforces git-trackable versioning, avoids inline string drift,
and enables rollbacks/diff tracking across prompt iterations.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

PROMPTS_DIR = Path(__file__).resolve().parent

DEFAULT_VERSIONS = {
    "agent_system": "v1.0",
    "grounded_qa": "v1.0",
    "document_extraction": "v1.0",
    "query_router": "v1.0"
}


class PromptManager:
    """Central prompt registry for SiteSense GenAI and Agentic modules."""

    @staticmethod
    def get_prompt(prompt_name: str, version: Optional[str] = None) -> str:
        """
        Loads the prompt text from its versioned file.
        Example: get_prompt('grounded_qa', 'v1.0') -> reads genai/prompts/grounded_qa_v1.0.txt
        """
        ver = version or DEFAULT_VERSIONS.get(prompt_name, "v1.0")
        filename = f"{prompt_name}_{ver}.txt"
        file_path = PROMPTS_DIR / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"Prompt file '{filename}' not found in {PROMPTS_DIR}. "
                f"Available prompts must be defined as versioned files."
            )

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    @staticmethod
    def list_prompts() -> Dict[str, str]:
        """Lists all registered prompt files and active versions."""
        prompts = {}
        for p in PROMPTS_DIR.glob("*_v*.txt"):
            stem = p.stem
            parts = stem.rsplit("_", 1)
            if len(parts) == 2:
                name, ver = parts
                prompts[name] = ver
        return prompts


prompt_manager = PromptManager()
