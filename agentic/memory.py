"""
SITESENSE - Conversation Memory & Context Management (Feature 4.9)
Handles short-term session conversation history and persistent per-site context.
"""

from typing import List, Dict, Any, Optional

class ConversationMemory:
    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self.sessions: Dict[str, List[Dict[str, Any]]] = {}

    def add_message(self, session_id: str, role: str, content: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append({"role": role, "content": content})
        # Keep within max turns (user + assistant pairs)
        if len(self.sessions[session_id]) > self.max_turns * 2:
            self.sessions[session_id] = self.sessions[session_id][-(self.max_turns * 2):]

    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        return self.sessions.get(session_id, [])

    def clear(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]

# Singleton memory manager
memory = ConversationMemory()

