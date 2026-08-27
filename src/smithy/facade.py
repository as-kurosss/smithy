"""Smithy — Facade for creating RPA bots with simple API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from smithy.core.context import ExecutionContext
from smithy.core.registry import ToolRegistry
from smithy.core.tool import Tool


@dataclass
class ProcessHandle:
    """Handle for a launched process. Contains PID for filtering UIA elements."""

    pid: int
    name: str


class Smithy:
    """Main SDK class for creating RPA bots.

    Usage::

        bot = Smithy(tools=[ClickTool(), FindTool()])
        app = await bot.process("notepad.exe")
        await bot.click(app, name="File")
    """

    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._registry = ToolRegistry()
        self._ctx = ExecutionContext.create()
        if tools:
            for t in tools:
                self._registry.register(t)

    @property
    def ctx(self) -> ExecutionContext:
        """Access the underlying execution context."""
        return self._ctx

    def register(self, tool: Tool) -> None:
        """Register a tool for use by this bot."""
        self._registry.register(tool)

    async def process(self, command: str, **kwargs: Any) -> ProcessHandle:
        """Launch a process and return a handle with PID.

        Args:
            command: Executable path or name (e.g. "notepad.exe").
            **kwargs: Additional parameters passed to the process tool.

        Returns:
            ProcessHandle with pid and name for filtering UIA elements.
        """
        result = await self._registry.execute(
            "process", {"action": "start", "command": command, **kwargs}, self._ctx
        )
        return ProcessHandle(pid=result["pid"], name=command)

    async def find(
        self, handle: ProcessHandle | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """Find a Windows UI element.

        Args:
            handle: ProcessHandle to filter by PID. If None, searches all windows.
            **kwargs: Selector fields (name, automation_id, control_type, etc.).

        Returns:
            Dict with "status" and "element" keys.
        """
        if handle:
            kwargs["pid"] = handle.pid
        result: dict[str, Any] = await self._registry.execute("find", kwargs, self._ctx)
        return result

    async def click(
        self, handle: ProcessHandle | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """Click a UI element.

        When *handle* is provided, the PID is forwarded to the click tool
        so it can narrow the UIA search scope automatically.

        Args:
            handle: ProcessHandle to scope element search by PID.
            **kwargs: Selector fields (name, automation_id, etc.) or
                "element" key for a pre-resolved element.

        Returns:
            Dict with "status" key.
        """
        if handle:
            kwargs.setdefault("pid", handle.pid)
        result: dict[str, Any] = await self._registry.execute(
            "click", kwargs, self._ctx
        )
        return result

    async def call(self, name: str, **kwargs: Any) -> Any:
        """Execute a tool by name. For custom and non-standard tools.

        Args:
            name: Tool name (e.g. "data.read_table", "http.request").
            **kwargs: Tool parameters.

        Returns:
            Tool execution result.
        """
        return await self._registry.execute(name, kwargs, self._ctx)
