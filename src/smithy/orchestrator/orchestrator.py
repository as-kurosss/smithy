"""Orchestrator — job management with asyncio tasks."""

from __future__ import annotations

import asyncio
import itertools
from typing import Any

from smithy.core.context import ExecutionContext
from smithy.core.registry import ToolRegistry
from smithy.engine.executor import RobotExecutor
from smithy.engine.robot import Robot
from smithy.orchestrator.job import Job, JobId, JobStatus


class OrchestratorError(Exception):
    """Error for orchestrator operations."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class JobNotFound(OrchestratorError):
    """Job not found."""

    def __init__(self, job_id: int) -> None:
        super().__init__(f"Job not found: {job_id}")
        self.job_id = job_id


class JobAlreadyFinished(OrchestratorError):
    """Job already finished."""

    def __init__(self, job_id: int) -> None:
        super().__init__(f"Job already finished: {job_id}")
        self.job_id = job_id


class Orchestrator:
    """Manages robot job execution lifecycle."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry
        self._jobs: dict[int, Job] = {}
        self._contexts: dict[int, ExecutionContext] = {}
        self._id_counter = itertools.count(0)
        self._tasks: dict[int, asyncio.Task[None]] = {}  # type: ignore[type-arg]

    def submit(self, robot: Robot) -> JobId:
        """Submit a robot for async execution. Returns JobId."""
        job_id = JobId(next(self._id_counter))
        ctx = ExecutionContext.create()
        self._contexts[job_id.value] = ctx
        job = Job.queued(job_id, robot.name)
        job.status = JobStatus.RUNNING
        self._jobs[job_id.value] = job

        task = asyncio.create_task(
            self._run_job(job_id, robot, ctx),
        )
        self._tasks[job_id.value] = task
        return job_id

    def cancel(self, job_id: JobId) -> None:
        """Cancel a running job.

        Raises JobNotFound or JobAlreadyFinished.
        """
        job = self._jobs.get(job_id.value)
        if job is None:
            raise JobNotFound(job_id.value)
        if job.status in (JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED):
            raise JobAlreadyFinished(job_id.value)
        # Cancel the asyncio task
        task = self._tasks.get(job_id.value)
        if task is not None:
            task.cancel()
        job.status = JobStatus.CANCELLED

    def get(self, job_id: JobId) -> Job | None:
        """Get a job by ID."""
        return self._jobs.get(job_id.value)

    def history(self) -> list[Job]:
        """Return all jobs sorted by ID."""
        return sorted(self._jobs.values(), key=lambda j: j.id.value)

    def context_snapshot(self, job_id: JobId) -> dict[str, Any]:
        """Get the context snapshot for a job."""
        ctx = self._contexts.get(job_id.value)
        if ctx is None:
            return {}
        snap = ctx.snapshot()
        return {k: v.value for k, v in snap.items()}

    async def _run_job(
        self,
        job_id: JobId,
        robot: Robot,
        ctx: ExecutionContext,
    ) -> None:
        """Execute a robot and update job status."""
        executor = RobotExecutor(self._registry, ctx)
        try:
            report = await executor.execute(robot)
            job = self._jobs.get(job_id.value)
            if job is not None:
                job.report = report
                job.status = (
                    JobStatus.SUCCEEDED if report.ok else JobStatus.FAILED
                )
        except asyncio.CancelledError:
            job = self._jobs.get(job_id.value)
            if job is not None:
                job.status = JobStatus.CANCELLED
        except Exception:
            job = self._jobs.get(job_id.value)
            if job is not None:
                job.status = JobStatus.FAILED
