"""Tests for smithy.orchestrator and smithy.engine.debug."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest

from smithy.core.registry import ToolRegistry
from smithy.engine.debug import DebugController, StepAction
from smithy.engine.robot import Robot, Step
from smithy.orchestrator.job import Job, JobId, JobStatus
from smithy.orchestrator.orchestrator import (
    JobAlreadyFinished,
    JobNotFound,
    Orchestrator,
)

# --- Helpers ---


def _make_tool(name: str, return_value: Any = "ok") -> AsyncMock:
    tool = AsyncMock()
    tool.name = name
    tool.execute.return_value = return_value
    return tool


def _simple_robot() -> Robot:
    return Robot(
        name="simple",
        version="1.0",
        steps=[Step(action="stub.tool", params={})],
    )


def _empty_robot() -> Robot:
    return Robot(name="empty", version="1.0", steps=[])


# --- Tests ---


class TestJobId:
    def test_str(self) -> None:
        jid = JobId(42)
        assert str(jid) == "42"

    def test_equality(self) -> None:
        assert JobId(1) == JobId(1)
        assert JobId(1) != JobId(2)


class TestJobStatus:
    def test_values(self) -> None:
        assert JobStatus.QUEUED == "queued"
        assert JobStatus.RUNNING == "running"
        assert JobStatus.SUCCEEDED == "succeeded"
        assert JobStatus.FAILED == "failed"
        assert JobStatus.CANCELLED == "cancelled"
        assert JobStatus.PAUSED == "paused"


class TestJob:
    def test_queued_factory(self) -> None:
        job = Job.queued(JobId(0), "test")
        assert job.id.value == 0
        assert job.robot_name == "test"
        assert job.status == JobStatus.QUEUED
        assert job.report is None
        assert job.finished_at is None


class TestOrchestrator:
    @pytest.mark.asyncio
    async def test_submit_returns_job_id(self) -> None:
        reg = ToolRegistry()
        reg.register(_make_tool("stub.tool"))
        orch = Orchestrator(reg)
        jid = orch.submit(_simple_robot())
        assert isinstance(jid, JobId)

    @pytest.mark.asyncio
    async def test_get_returns_job(self) -> None:
        reg = ToolRegistry()
        reg.register(_make_tool("stub.tool"))
        orch = Orchestrator(reg)
        jid = orch.submit(_simple_robot())
        job = orch.get(jid)
        assert job is not None
        assert job.robot_name == "simple"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self) -> None:
        orch = Orchestrator(ToolRegistry())
        assert orch.get(JobId(999)) is None

    @pytest.mark.asyncio
    async def test_empty_robot_succeeds(self) -> None:
        reg = ToolRegistry()
        orch = Orchestrator(reg)
        jid = orch.submit(_empty_robot())
        # Wait for task to complete
        await asyncio.sleep(0.1)
        job = orch.get(jid)
        assert job is not None
        assert job.status == JobStatus.SUCCEEDED

    @pytest.mark.asyncio
    async def test_history_sorted_by_id(self) -> None:
        reg = ToolRegistry()
        reg.register(_make_tool("stub.tool"))
        orch = Orchestrator(reg)
        id1 = orch.submit(_simple_robot())
        id2 = orch.submit(_simple_robot())
        history = orch.history()
        assert len(history) == 2
        assert history[0].id == id1
        assert history[1].id == id2

    @pytest.mark.asyncio
    async def test_cancel_running_job(self) -> None:
        # Create a slow tool
        slow_tool = AsyncMock()
        slow_tool.name = "slow.tool"

        async def slow_execute(*args: Any, **kwargs: Any) -> str:
            await asyncio.sleep(10)
            return "done"

        slow_tool.execute = slow_execute

        reg = ToolRegistry()
        reg.register(slow_tool)
        orch = Orchestrator(reg)

        robot = Robot(
            name="slow",
            version="1.0",
            steps=[Step(action="slow.tool", params={})],
        )
        jid = orch.submit(robot)
        await asyncio.sleep(0.05)  # Let task start

        orch.cancel(jid)
        job = orch.get(jid)
        assert job is not None
        assert job.status == JobStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_raises(self) -> None:
        orch = Orchestrator(ToolRegistry())
        with pytest.raises(JobNotFound):
            orch.cancel(JobId(999))

    @pytest.mark.asyncio
    async def test_cancel_finished_job_raises(self) -> None:
        reg = ToolRegistry()
        orch = Orchestrator(reg)
        jid = orch.submit(_empty_robot())
        await asyncio.sleep(0.1)  # Let it finish
        with pytest.raises(JobAlreadyFinished):
            orch.cancel(jid)

    @pytest.mark.asyncio
    async def test_context_snapshot(self) -> None:
        reg = ToolRegistry()
        reg.register(_make_tool("stub.tool", return_value="hello"))
        orch = Orchestrator(reg)

        robot = Robot(
            name="r",
            version="1.0",
            steps=[Step(action="stub.tool", params={}, outputs={"out": "var"})],
        )
        jid = orch.submit(robot)
        await asyncio.sleep(0.1)

        snap = orch.context_snapshot(jid)
        assert "var" in snap


class TestDebugController:
    @pytest.mark.asyncio
    async def test_no_breakpoints_returns_execute(self) -> None:
        dc = DebugController()
        assert await dc.should_continue(0) == StepAction.EXECUTE
        assert await dc.should_continue(1) == StepAction.EXECUTE
        assert await dc.should_continue(5) == StepAction.EXECUTE

    @pytest.mark.asyncio
    async def test_breakpoint_pauses(self) -> None:
        dc = DebugController()
        await dc.add_breakpoint(2)

        # Steps 0, 1 — Execute
        assert await dc.should_continue(0) == StepAction.EXECUTE
        assert await dc.should_continue(1) == StepAction.EXECUTE

        # Step 2 — will pause, start in background
        async def pause_at_2() -> StepAction:
            return await dc.should_continue(2)

        task = asyncio.create_task(pause_at_2())
        await asyncio.sleep(0.05)
        assert dc.is_paused()

        # Resume
        dc.continue_execution()
        result = await asyncio.wait_for(task, timeout=1.0)
        assert result == StepAction.PAUSE

    @pytest.mark.asyncio
    async def test_set_breakpoints_replaces_all(self) -> None:
        dc = DebugController()
        await dc.add_breakpoint(0)
        await dc.add_breakpoint(1)

        await dc.set_breakpoints({5})

        assert await dc.should_continue(0) == StepAction.EXECUTE
        assert await dc.should_continue(1) == StepAction.EXECUTE

        async def pause_at_5() -> StepAction:
            return await dc.should_continue(5)

        task = asyncio.create_task(pause_at_5())
        await asyncio.sleep(0.05)
        assert dc.is_paused()
        dc.continue_execution()
        await asyncio.wait_for(task, timeout=1.0)

    @pytest.mark.asyncio
    async def test_step_over(self) -> None:
        dc = DebugController()
        assert not dc.is_paused()

        dc.step_over()
        assert not dc.is_paused()

        # check_step_over sets paused
        assert dc.check_step_over()
        assert dc.is_paused()

        # should_continue with resume_flag returns Execute
        result = await asyncio.wait_for(dc.should_continue(1), timeout=1.0)
        assert result == StepAction.EXECUTE

    def test_update_step(self) -> None:
        dc = DebugController()
        assert dc.current_step() == 0
        dc.update_step(3)
        assert dc.current_step() == 3

    @pytest.mark.asyncio
    async def test_remove_breakpoint(self) -> None:
        dc = DebugController()
        dc._breakpoints = {0, 1, 2}
        await dc.remove_breakpoint(1)
        assert dc._breakpoints == {0, 2}
