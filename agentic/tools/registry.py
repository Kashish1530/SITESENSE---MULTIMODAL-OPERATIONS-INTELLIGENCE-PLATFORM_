"""
Central Tool Registry for the SiteSense agent.

Registers callable Python tools and generates OpenAI-compatible
function schemas for the agent reasoning loop.
"""

from typing import Dict, Any, Callable, List


class ToolRegistry:
    """Stores tool implementations and their JSON function schemas."""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, description: str, parameters: Dict[str, Any]):
        """Decorator to register a tool along with its parameter schema."""
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
        """Returns list of function schemas formatted for LLM tool calling."""
        return list(self._schemas.values())

    def list_tool_names(self) -> List[str]:
        return list(self._tools.keys())

    def execute(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a registered tool with error handling."""
        func = self._tools.get(name)
        if not func:
            return {
                "success": False,
                "error": f"Tool '{name}' is not registered in ToolRegistry."
            }
        try:
            res = func(**args)
            return {"success": True, "result": res}
        except Exception as err:
            return {"success": False, "error": f"Error executing tool '{name}': {str(err)}"}


# Global registry singleton
registry = ToolRegistry()
