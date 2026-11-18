"""
SITESENSE - Central Tool Registry (Feature 4.1)
Defines tool schemas and handles safe dispatch for the Agent Reason-Act Loop.
"""

from typing import Dict, Any, Callable, List
import json

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, description: str, parameters: Dict[str, Any]):
        """Decorator to register a tool with its OpenAI-compatible JSON schema."""
        def decorator(func: Callable):
            self._tools[name] = func
            self._schemas[name] = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters,
                }
            }
            return func
        return decorator

    def get_tool(self, name: str) -> Callable:
        return self._tools.get(name)

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Returns tool schemas formatted for LLM function calling."""
        return list(self._schemas.values())

    def list_tool_names(self) -> List[str]:
        return list(self._tools.keys())

    def execute(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Safely executes a registered tool and catches errors."""
        func = self._tools.get(name)
        if not func:
            return {
                "success": False,
                "error": f"Tool '{name}' is not registered in ToolRegistry."
            }
        try:
            result = func(**args)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": f"Error executing tool '{name}': {str(e)}"}

# Global tool registry singleton
registry = ToolRegistry()

