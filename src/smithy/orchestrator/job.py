"""Job, JobId, JobStatus — job lifecycle models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class JobStatus(StrEnum):
    """Status of a job execution."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class JobId:
    """Unique job identifier."""

    value: int

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class Job:
    """A single job execution record."""

    id: JobId
    robot_name: str
    status: JobStatus = JobStatus.QUEUED
    report: Any = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None

    @classmethod
    def queued(cls, job_id: JobId, robot_name: str) -> Job:
        """Create a new queued job."""
        return cls(id=job_id, robot_name=robot_name, status=JobStatus.QUEUED)
