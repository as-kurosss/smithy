"""Smithy — Facade for creating RPA bots with simple API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from smithy.core.context import ExecutionContext
from smithy.core.registry import ToolRegistry
from smithy.core.tool import Tool


class _SupportsPid(Protocol):
    pid: int


@dataclass(frozen=True)
class ProcessHandle:
    """Handle for a launched process. Contains PID for filtering UIA elements."""

    pid: int
    name: str


@dataclass(frozen=True)
class FindResult:
    """Result of a find operation."""

    status: str


@dataclass(frozen=True)
class ClickResult:
    """Result of a click operation."""

    status: str


class Smithy:
    """Main SDK class for creating RPA bots.

    Usage::

        bot = Smithy(tools=[ClickTool(), FindTool()])
        app = await bot.process_run("notepad.exe")
        await bot.click(app, name="File")
        await bot.process_stop(app)
    """

    def __init__(self, *, tools: list[Tool] | None = None) -> None:
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

    async def process_run(self, command: str, **kwargs: Any) -> ProcessHandle:
        """Launch a process and return a handle with PID.

        Args:
            command: Executable path or name (e.g. "notepad.exe").
            **kwargs: Additional parameters passed to the process tool.

        Returns:
            ProcessHandle with pid and name for filtering UIA elements.
        """
        result = await self._registry.execute(
            "windows.process", {"action": "start", "command": command, **kwargs}, self._ctx
        )
        return ProcessHandle(pid=result["pid"], name=command)

    async def process_stop(
        self,
        handle: ProcessHandle | None = None,
        *,
        pid: int | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Stop a running process.

        Provide *handle*, *pid*, or *name* to identify the process.

        Args:
            handle: ProcessHandle to stop.
            pid: Process ID to stop.
            name: Process image name to stop (e.g. "notepad.exe").

        Returns:
            Dict with "status" key.
        """
        result: dict[str, Any]
        if handle is not None:
            result = await self._registry.execute(
                "windows.process", {"action": "stop", "pid": handle.pid}, self._ctx
            )
        elif pid is not None:
            result = await self._registry.execute(
                "windows.process", {"action": "stop", "pid": pid}, self._ctx
            )
        elif name is not None:
            result = await self._registry.execute(
                "windows.process", {"action": "stop", "name": name}, self._ctx
            )
        else:
            raise ValueError("Provide handle, pid, or name")
        return result

    async def find(
        self,
        handle: _SupportsPid | None = None,
        **kwargs: Any,
    ) -> FindResult:
        """Find a Windows UI element.

        Args:
            handle: ProcessHandle to filter by PID. If None, searches all windows.
            **kwargs: Selector fields (name, automation_id, control_type, etc.).

        Returns:
            FindResult.
        """
        if handle is not None:
            kwargs.setdefault("pid", handle.pid)
        result = await self._registry.execute("windows.find", kwargs, self._ctx)
        return FindResult(status=result.get("status", "found"))

    async def click(
        self,
        handle: _SupportsPid | None = None,
        **kwargs: Any,
    ) -> ClickResult:
        """Click a UI element.

        When *handle* is provided, the PID is forwarded to the click tool
        so it can narrow the UIA search scope automatically.

        Args:
            handle: ProcessHandle to scope element search by PID.
            **kwargs: Selector fields (name, automation_id, etc.) or
                "element" key for a pre-resolved element.

        Returns:
            ClickResult.
        """
        if handle is not None:
            kwargs.setdefault("pid", handle.pid)
        result = await self._registry.execute("windows.click", kwargs, self._ctx)
        return ClickResult(status=result.get("status", "clicked"))

    async def wait(
        self,
        handle: _SupportsPid | None = None,
        *,
        name: str | None = None,
        automation_id: str | None = None,
        control_type: str | None = None,
        class_name: str | None = None,
        pid: int | None = None,
        timeout_ms: int = 10000,
        interval_ms: int = 500,
    ) -> bool:
        """Wait for a UI element to appear.

        Polls the desktop for a matching element at *interval_ms*
        until found or *timeout_ms* elapsed.

        Args:
            handle: ProcessHandle to scope the search by PID.
            name: Element name to match (supports wildcards: * and ?).
            automation_id: UI Automation identifier.
            control_type: Control type (e.g. Button, Edit, Window).
            class_name: Window class name.
            pid: Process ID filter.
            timeout_ms: Maximum wait time in milliseconds.
            interval_ms: Polling interval in milliseconds.

        Returns:
            ``True`` if the element was found, ``False`` otherwise.
        """
        config: dict[str, Any] = {}
        if handle is not None:
            config["pid"] = handle.pid
        if name is not None:
            config["name"] = name
        if automation_id is not None:
            config["automation_id"] = automation_id
        if control_type is not None:
            config["control_type"] = control_type
        if class_name is not None:
            config["class_name"] = class_name
        if pid is not None:
            config["pid"] = pid
        config["timeout_ms"] = timeout_ms
        config["interval_ms"] = interval_ms
        result = await self._registry.execute("windows.wait", config, self._ctx)
        return bool(result)

    async def delay(self, duration_ms: int) -> None:
        """Pause bot execution for a specified duration.

        Args:
            duration_ms: Delay duration in milliseconds.
        """
        await self._registry.execute(
            "windows.delay", {"duration_ms": duration_ms}, self._ctx
        )

    async def call(self, name: str, **kwargs: Any) -> Any:
        """Execute a tool by name. For custom and non-standard tools.

        Args:
            name: Tool name (e.g. "data.read_table").
            **kwargs: Tool parameters.

        Returns:
            Tool execution result.
        """
        return await self._registry.execute(name, kwargs, self._ctx)
        return await self._registry.execute(name, kwargs, self._ctx)
