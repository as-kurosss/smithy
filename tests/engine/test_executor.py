"""Tests for smithy.engine.executor — RobotExecutor."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from smithy.core.context import ExecutionContext
from smithy.core.errors import InvalidInput
from smithy.core.registry import ToolRegistry
from smithy.engine.executor import ExecutionReport, RobotExecutor, StepResult
from smithy.engine.robot import Robot, Step

# --- Helpers ---


def _make_tool(name: str, return_value: Any = "ok") -> AsyncMock:
    """Create a mock tool."""
    tool = AsyncMock()
    tool.name = name
    tool.execute.return_value = return_value
    return tool


def _make_robot(*actions: str) -> Robot:
    """Create a robot with simple steps."""
    return Robot(
        name="test",
        version="1.0",
        steps=[Step(action=a, params={}) for a in actions],
    )


# --- Tests ---


class TestStepResult:
    def test_step_result_ok(self) -> None:
        r = StepResult(step_index=0, action="click", output={"clicked": True})
        assert r.ok is True
        assert r.error is None
        assert r.output == {"clicked": True}

    def test_step_result_error(self) -> None:
        err = InvalidInput("bad")
        r = StepResult(step_index=1, action="click", error=err)
        assert r.ok is False
        assert r.error is err


class TestExecutionReport:
    def test_report_fields(self) -> None:
        steps = [StepResult(step_index=0, action="a", output="ok")]
        report = ExecutionReport(robot_name="R", steps=steps, duration_ms=123.4)
        assert report.robot_name == "R"
        assert report.ok is True
        assert report.steps[0].action == "a"
        assert report.duration_ms == 123.4

    def test_report_not_ok_on_error(self) -> None:
        steps = [
            StepResult(step_index=0, action="a", output="ok"),
            StepResult(step_index=1, action="b", error=InvalidInput("fail")),
        ]
        report = ExecutionReport(robot_name="R", steps=steps, duration_ms=0.0)
        assert report.ok is False


class TestRobotExecutor:
    @pytest.mark.asyncio
    async def test_execute_empty_robot(self) -> None:
        robot = Robot(name="empty", version="1.0", steps=[])
        reg = ToolRegistry()
        ctx = ExecutionContext.create()
        executor = RobotExecutor(reg, ctx)
        report = await executor.execute(robot)
        assert report.ok is True
        assert len(report.steps) == 0

    @pytest.mark.asyncio
    async def test_execute_single_step(self) -> None:
        robot = _make_robot("stub.tool")
        reg = ToolRegistry()
        tool = _make_tool("stub.tool", return_value="done")
        reg.register(tool)
        ctx = ExecutionContext.create()
        executor = RobotExecutor(reg, ctx)
        report = await executor.execute(robot)
        assert report.ok is True
        assert len(report.steps) == 1
        assert report.steps[0].output == "done"
        tool.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_multiple_steps(self) -> None:
        robot = _make_robot("a", "b", "c")
        reg = ToolRegistry()
        for name in ("a", "b", "c"):
            reg.register(_make_tool(name, return_value=f"{name}_out"))
        ctx = ExecutionContext.create()
        executor = RobotExecutor(reg, ctx)
        report = await executor.execute(robot)
        assert report.ok is True
        assert len(report.steps) == 3
        assert [s.output for s in report.steps] == ["a_out", "b_out", "c_out"]

    @pytest.mark.asyncio
    async def test_execute_step_outputs_stored_in_context(self) -> None:
        step = Step(
            action="get_name",
            params={},
            outputs={"result": "user_name"},
        )
        robot = Robot(name="r", version="1.0", steps=[step])
        reg = ToolRegistry()
        reg.register(_make_tool("get_name", return_value="Alice"))
        ctx = ExecutionContext.create()
        executor = RobotExecutor(reg, ctx)
        await executor.execute(robot)
        val = ctx.get("user_name")
        assert val is not None
        assert val.as_string() == "Alice"

    @pytest.mark.asyncio
    async def test_execute_stop_on_error(self) -> None:
        robot = Robot(
            name="r",
            version="1.0",
            steps=[
                Step(action="fail_tool", params={}),
                Step(action="never_reach", params={}),
            ],
        )
        reg = ToolRegistry()
        fail_tool = AsyncMock()
        fail_tool.name = "fail_tool"
        fail_tool.execute.side_effect = InvalidInput("boom")
        reg.register(fail_tool)
        ctx = ExecutionContext.create()
        executor = RobotExecutor(reg, ctx)
        report = await executor.execute(robot)
        assert report.ok is False
        assert len(report.steps) == 1
        assert "never_reach" not in [s.action for s in report.steps]

    @pytest.mark.asyncio
    async def test_execute_continue_on_error(self) -> None:
        robot = Robot(
            name="r",
            version="1.0",
            steps=[
                Step(action="fail_tool", params={}, stop_on_error=False),
                Step(action="ok_tool", params={}),
            ],
        )
        reg = ToolRegistry()
        fail_tool = AsyncMock()
        fail_tool.name = "fail_tool"
        fail_tool.execute.side_effect = InvalidInput("boom")
        reg.register(fail_tool)
        reg.register(_make_tool("ok_tool"))
        ctx = ExecutionContext.create()
        executor = RobotExecutor(reg, ctx)
        report = await executor.execute(robot)
        assert report.ok is False
        assert len(report.steps) == 2

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self) -> None:
        robot = _make_robot("no.such.tool")
        reg = ToolRegistry()
        ctx = ExecutionContext.create()
        executor = RobotExecutor(reg, ctx)
        report = await executor.execute(robot)
        assert report.ok is False
        assert report.steps[0].error is not None
