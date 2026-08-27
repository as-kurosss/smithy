"""Tests for smithy.facade — Smithy facade class and ProcessHandle."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from smithy.core.context import ExecutionContext
from smithy.core.errors import InvalidInput
from smithy.core.tool import AbstractTool
from smithy.facade import ProcessHandle, Smithy

# --- Stubs ---


class StubTool(AbstractTool):
    """Minimal tool for testing facade dispatch."""

    def __init__(
        self,
        tool_name: str = "stub.tool",
        output: Any = "ok",
    ) -> None:
        self._name = tool_name
        self._output = output

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "Stub tool for testing."

    async def execute(
        self,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> Any:
        return self._output


class ProcessStub(AbstractTool):
    """Stub for windows.process tool."""

    @property
    def name(self) -> str:
        return "process"

    @property
    def description(self) -> str:
        return "Process stub."

    async def execute(
        self,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> Any:
        return {"status": "started", "pid": 12345}


class FindStub(AbstractTool):
    """Stub for windows.find tool."""

    @property
    def name(self) -> str:
        return "find"

    @property
    def description(self) -> str:
        return "Find stub."

    async def execute(
        self,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> Any:
        return {"status": "found", "element": MagicMock()}


class ClickStub(AbstractTool):
    """Stub for windows.click tool."""

    @property
    def name(self) -> str:
        return "click"

    @property
    def description(self) -> str:
        return "Click stub."

    async def execute(
        self,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> Any:
        return {"status": "clicked"}


class FailFindStub(AbstractTool):
    """Stub that returns no element."""

    @property
    def name(self) -> str:
        return "find"

    @property
    def description(self) -> str:
        return "Fail find."

    async def execute(
        self,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> Any:
        return {"status": "not_found"}


# --- Tests ---


class TestProcessHandle:
    def test_creation(self) -> None:
        h = ProcessHandle(pid=123, name="notepad.exe")
        assert h.pid == 123
        assert h.name == "notepad.exe"

    def test_equality(self) -> None:
        a = ProcessHandle(pid=1, name="a")
        b = ProcessHandle(pid=1, name="a")
        assert a == b


class TestSmithyInit:
    def test_empty(self) -> None:
        bot = Smithy()
        assert bot._registry.list_tools() == []

    def test_with_tools(self) -> None:
        bot = Smithy(tools=[StubTool(tool_name="a"), StubTool(tool_name="b")])
        assert sorted(bot._registry.list_tools()) == ["a", "b"]

    def test_register(self) -> None:
        bot = Smithy()
        bot.register(StubTool(tool_name="x"))
        assert bot._registry.get("x") is not None

    def test_ctx_property(self) -> None:
        bot = Smithy()
        assert isinstance(bot.ctx, ExecutionContext)


class TestSmithyProcess:
    @pytest.mark.asyncio
    async def test_process_returns_handle(self) -> None:
        bot = Smithy(tools=[ProcessStub()])
        handle = await bot.process("notepad.exe")
        assert isinstance(handle, ProcessHandle)
        assert handle.pid == 12345
        assert handle.name == "notepad.exe"

    @pytest.mark.asyncio
    async def test_process_no_tool_raises(self) -> None:
        bot = Smithy()
        with pytest.raises(InvalidInput, match="not found"):
            await bot.process("notepad.exe")


class TestSmithyFind:
    @pytest.mark.asyncio
    async def test_find_with_handle(self) -> None:
        bot = Smithy(tools=[FindStub()])
        handle = ProcessHandle(pid=42, name="app")
        result = await bot.find(handle, name="OK")
        assert result["status"] == "found"

    @pytest.mark.asyncio
    async def test_find_without_handle(self) -> None:
        bot = Smithy(tools=[FindStub()])
        result = await bot.find(name="OK")
        assert result["status"] == "found"


class TestSmithyClick:
    @pytest.mark.asyncio
    async def test_click_with_handle(self) -> None:
        bot = Smithy(tools=[ClickStub()])
        handle = ProcessHandle(pid=42, name="app")
        result = await bot.click(handle, name="OK")
        assert result["status"] == "clicked"

    @pytest.mark.asyncio
    async def test_click_without_handle(self) -> None:
        bot = Smithy(tools=[ClickStub()])
        result = await bot.click(name="OK")
        assert result["status"] == "clicked"

    @pytest.mark.asyncio
    async def test_click_with_element_key(self) -> None:
        bot = Smithy(tools=[ClickStub()])
        result = await bot.click(element_key="my_elem")
        assert result["status"] == "clicked"

    @pytest.mark.asyncio
    async def test_click_pid_forwarded(self) -> None:
        """PID from handle should be in kwargs passed to tool."""
        received: dict[str, Any] = {}

        class CaptureClick(AbstractTool):
            @property
            def name(self) -> str:
                return "click"

            @property
            def description(self) -> str:
                return "Capture."

            async def execute(
                self,
                config: dict[str, Any],
                ctx: ExecutionContext,
            ) -> Any:
                received.update(config)
                return {"status": "clicked"}

        bot = Smithy(tools=[CaptureClick()])
        handle = ProcessHandle(pid=99, name="app")
        await bot.click(handle, name="Button")
        assert received["pid"] == 99
        assert received["name"] == "Button"

    @pytest.mark.asyncio
    async def test_click_explicit_pid_not_overridden(self) -> None:
        """If user passes pid explicitly, handle should not override it."""
        received: dict[str, Any] = {}

        class CaptureClick(AbstractTool):
            @property
            def name(self) -> str:
                return "click"

            @property
            def description(self) -> str:
                return "Capture."

            async def execute(
                self,
                config: dict[str, Any],
                ctx: ExecutionContext,
            ) -> Any:
                received.update(config)
                return {"status": "clicked"}

        bot = Smithy(tools=[CaptureClick()])
        handle = ProcessHandle(pid=99, name="app")
        await bot.click(handle, name="Button", pid=55)
        assert received["pid"] == 55  # explicit pid wins


class TestSmithyCall:
    @pytest.mark.asyncio
    async def test_call_custom_tool(self) -> None:
        bot = Smithy(tools=[StubTool(tool_name="custom", output="done")])
        result = await bot.call("custom")
        assert result == "done"

    @pytest.mark.asyncio
    async def test_call_nonexistent_raises(self) -> None:
        bot = Smithy()
        with pytest.raises(InvalidInput, match="not found"):
            await bot.call("no.such.tool")
