"""Tool protocol and dynamic dispatch wrapper."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from smithy.core.context import ExecutionContext


@runtime_checkable
class Tool(Protocol):
    """Protocol for all automation tools.

    Each tool has typed Input/Output, a unique name, description,
    JSON Schema, and an async execute method.
    """

    @property
    def name(self) -> str:
        """Unique tool name (e.g. 'windows.click')."""
        ...

    @property
    def description(self) -> str:
        """Description for documentation and LLM agents."""
        ...

    def schema(self) -> dict[str, Any]:
        """JSON Schema for input validation."""
        ...

    async def execute(
        self,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> Any:
        """Execute the tool with JSON-serialized parameters.

        Returns JSON-serializable output on success.
        Raises ToolError on failure.
        """
        ...


class AbstractTool(ABC):
    """Base class for tool implementations."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    def schema(self) -> dict[str, Any]:
        return {}

    @abstractmethod
    async def execute(
        self,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> Any: ...
