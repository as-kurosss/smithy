"""Tool registry for centralized management and execution."""

from __future__ import annotations

from typing import Any

from smithy.core.errors import InvalidInput
from smithy.core.tool import Tool


class ToolRegistry:
    """Registry of tools keyed by name.

    Stores tools and dispatches execute calls by name.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool by its name property."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Get a registered tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """Return names of all registered tools."""
        return sorted(self._tools.keys())

    async def execute(
        self,
        name: str,
        config: dict[str, Any],
    ) -> Any:
        """Execute a tool by name with JSON parameters.

        Raises InvalidInput if the tool is not found.
        """
        tool = self.get(name)
        if tool is None:
            raise InvalidInput(f"Tool '{name}' not found")
        return await tool.execute(config)
