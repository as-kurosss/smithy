"""Tool protocol and dynamic dispatch wrapper."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from functools import wraps
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


def tool(
    tool_name: str,
    tool_description: str = "",
) -> Callable[[Any], AbstractTool]:
    """Decorator to create a Tool from a function.

    Usage::

        @tool("greet", description="Greet a person")
        async def greet(config: dict, ctx: ExecutionContext) -> dict:
            name = config.get("name", "World")
            return {"message": f"Hello, {name}!"}

        bot = Smithy(tools=[greet])
        await bot.call("greet", name="Alice")

    Args:
        tool_name: Unique tool name.
        tool_description: Human-readable description. Uses function docstring if empty.

    Returns:
        An AbstractTool instance ready for registration.
    """

    def decorator(fn: Any) -> AbstractTool:
        doc = tool_description or (fn.__doc__ or "")

        @wraps(fn)
        class _DecoratedTool(AbstractTool):
            @property
            def name(self) -> str:
                return tool_name

            @property
            def description(self) -> str:
                return doc

            async def execute(
                self,
                config: dict[str, Any],
                ctx: ExecutionContext,
            ) -> Any:
                return await fn(config, ctx)

        return _DecoratedTool()

    return decorator
