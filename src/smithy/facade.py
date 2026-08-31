"""Smithy — Facade for creating RPA bots with simple API."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from smithy.core.events import EventBus, ToolEvent
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
class ClickResult:
    """Result of a click operation."""

    status: str


@dataclass(frozen=True)
class InputTextResult:
    """Result of an input_text operation."""

    status: str


@dataclass(frozen=True)
class SetTextResult:
    """Result of a set_text operation."""

    status: str


class Smithy:
    """Main SDK class for creating RPA bots.

    Usage::

        bot = Smithy(tools=[ClickTool()])
        app = await bot.process_run("notepad.exe")
        await bot.click(app, name="File")
        await bot.process_stop(app)
    """

    def __init__(self, *, tools: list[Tool] | None = None) -> None:
        self._registry = ToolRegistry()
        self._event_bus = EventBus()
        if tools:
            for t in tools:
                self._registry.register(t)

    def register(self, tool: Tool) -> None:
        """Register a tool for use by this bot."""
        self._registry.register(tool)

    def add_middleware(self, middleware: Any) -> None:
        """Add a middleware to the event pipeline.

        Args:
            middleware: An async callable that receives a ToolEvent
                and returns a ToolEvent or None to stop propagation.
        """
        self._event_bus.add_middleware(middleware)

    async def _execute(self, tool_name: str, config: dict[str, Any]) -> Any:
        """Execute a tool, capture timing, and emit event through middleware."""
        start = time.perf_counter()
        error: Exception | None = None
        result: Any = None
        try:
            result = await self._registry.execute(tool_name, config)
        except Exception as exc:
            error = exc
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            event = ToolEvent(
                tool_name=tool_name,
                config=config,
                result=result,
                error=error,
                duration_ms=elapsed_ms,
            )
            await self._event_bus.emit(event)
        return result

    async def process_run(self, command: str, **kwargs: Any) -> ProcessHandle:
        """Launch a process and return a handle with PID.

        Args:
            command: Executable path or name (e.g. "notepad.exe").
            **kwargs: Additional parameters passed to the process tool.

        Returns:
            ProcessHandle with pid and name for filtering UIA elements.
        """
        result = await self._execute(
            "windows.process", {"action": "start", "command": command, **kwargs}
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
            result = await self._execute(
                "windows.process", {"action": "stop", "pid": handle.pid}
            )
        elif pid is not None:
            result = await self._execute(
                "windows.process", {"action": "stop", "pid": pid}
            )
        elif name is not None:
            result = await self._execute(
                "windows.process", {"action": "stop", "name": name}
            )
        else:
            raise ValueError("Provide handle, pid, or name")
        return result

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
        result = await self._execute("windows.click", kwargs)
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
        result = await self._execute("windows.wait", config)
        return bool(result)

    async def delay(self, duration_ms: int) -> None:
        """Pause bot execution for a specified duration.

        Args:
            duration_ms: Delay duration in milliseconds.
        """
        await self._execute(
            "windows.delay", {"duration_ms": duration_ms}
        )

    async def screenshot(
        self,
        path: str,
        handle: _SupportsPid | None = None,
        *,
        pid: int | None = None,
        image_format: str = "png",
    ) -> dict[str, Any]:
        """Capture a screenshot and save it to a file.

        Requires ``mss`` and ``Pillow`` (included in ``smithy[windows]``).

        Args:
            path: File path to save the screenshot.
            handle: ProcessHandle to capture that window.
            pid: Process ID to capture that window.
            image_format: Image format — ``"png"`` (default) or ``"jpg"``.

        Returns:
            Dict with ``"status"``, ``"path"``, and ``"format"`` keys.
        """
        config: dict[str, Any] = {"path": path, "format": image_format}
        if handle is not None:
            config["pid"] = handle.pid
        elif pid is not None:
            config["pid"] = pid
        out: dict[str, Any] = await self._execute(
            "windows.screenshot", config
        )
        return out

    async def input_text(
        self,
        handle: _SupportsPid | None = None,
        *,
        text: str,
        **kwargs: Any,
    ) -> InputTextResult:
        """Type plain text into a UI element or the focused window.

        If *handle* or selector fields are provided, focuses the
        element first.  Otherwise types into the focused window.

        Args:
            handle: ProcessHandle to scope element search by PID.
            text: Plain text to type.
            **kwargs: ``element_key`` or selector fields (name,
                automation_id, control_type, class_name, pid).

        Returns:
            InputTextResult.
        """
        if handle is not None:
            kwargs.setdefault("pid", handle.pid)
        result = await self._execute(
            "windows.input_text", {"text": text, **kwargs}
        )
        return InputTextResult(status=result.get("status", "typed"))

    async def keyboard(
        self,
        handle: _SupportsPid | None = None,
        *,
        keys: str,
        **kwargs: Any,
    ) -> InputTextResult:
        """Send key combinations and key presses.

        Bracketed tokens are key events; everything else is plain text.
        ``[CTRL]S`` — hold Ctrl, type S.  ``[CTRL!]S`` — tap Ctrl, type S.

        If *handle* or selector fields are provided, focuses the
        element first.  Otherwise sends keys to the focused window.

        Args:
            handle: ProcessHandle to scope element search by PID.
            keys: Key presses with bracket syntax.
            **kwargs: ``element_key`` or selector fields (name,
                automation_id, control_type, class_name, pid).

        Returns:
            InputTextResult.
        """
        if handle is not None:
            kwargs.setdefault("pid", handle.pid)
        result = await self._execute(
            "windows.keyboard", {"keys": keys, **kwargs}
        )
        return InputTextResult(status=result.get("status", "sent"))

    async def set_text(
        self,
        handle: _SupportsPid | None = None,
        *,
        text: str,
        **kwargs: Any,
    ) -> SetTextResult:
        """Replace the entire text of a UI element via UIA ValuePattern.

        Args:
            handle: ProcessHandle to scope element search by PID.
            text: Text to set.
            **kwargs: ``element_key`` or selector fields (name,
                automation_id, control_type, class_name, pid).

        Returns:
            SetTextResult.
        """
        if handle is not None:
            kwargs.setdefault("pid", handle.pid)
        result = await self._execute(
            "windows.set_text", {"text": text, **kwargs}
        )
        return SetTextResult(status=result.get("status", "set"))

    async def get_element(
        self,
        handle: _SupportsPid | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Read a UI element's attributes.

        Args:
            handle: ProcessHandle to scope element search by PID.
            **kwargs: ``element_key`` or selector fields (name,
                automation_id, control_type, class_name, pid).

        Returns:
            Dict describing the element (name, control_type,
            automation_id, class_name, pid, rect).
        """
        if handle is not None:
            kwargs.setdefault("pid", handle.pid)
        out: dict[str, Any] = await self._execute(
            "windows.get_element", kwargs
        )
        return out

    async def call(self, name: str, **kwargs: Any) -> Any:
        """Execute a tool by name. For custom and non-standard tools.

        Args:
            name: Tool name (e.g. "data.read_table").
            **kwargs: Tool parameters.

        Returns:
            Tool execution result.
        """
        return await self._execute(name, kwargs)
