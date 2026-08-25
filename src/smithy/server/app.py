"""FastAPI REST server — bridge between Tauri and Python engine."""

from __future__ import annotations

import contextlib
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from smithy.core.registry import ToolRegistry
from smithy.engine.robot import Robot
from smithy.orchestrator.job import JobId
from smithy.orchestrator.orchestrator import (
    JobAlreadyFinished,
    JobNotFound,
    Orchestrator,
)

app = FastAPI(title="Smithy", version="0.1.0")

# Global state — initialized on startup
_registry: ToolRegistry | None = None
_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    """Get the global orchestrator instance."""
    if _orchestrator is None:
        raise RuntimeError("Orchestrator not initialized")
    return _orchestrator


def init_server(registry: ToolRegistry) -> None:
    """Initialize the server with a tool registry."""
    global _registry, _orchestrator
    _registry = registry
    _orchestrator = Orchestrator(registry)


# --- Request/Response models ---


class ParseRobotRequest(BaseModel):
    """Request for parsing a robot JSON."""

    robot_json: str


class RunRobotRequest(BaseModel):
    """Request for running a robot."""

    robot: dict[str, Any]


class SaveFileRequest(BaseModel):
    """Request for saving a file."""

    path: str
    content: str


class RunDebugRequest(BaseModel):
    """Request for running a robot in debug mode."""

    robot: dict[str, Any]
    breakpoints: list[int] = []


class SetBreakpointsRequest(BaseModel):
    """Request for setting breakpoints."""

    breakpoints: list[int]


# --- Endpoints ---


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/parse-robot")
async def parse_robot(req: ParseRobotRequest) -> dict[str, Any]:
    """Parse a robot JSON and return the parsed robot."""
    try:
        robot = Robot.model_validate_json(req.robot_json)
        return robot.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/run-robot")
async def run_robot(req: RunRobotRequest) -> dict[str, Any]:
    """Submit a robot for async execution."""
    try:
        robot = Robot(**req.robot)
        orch = get_orchestrator()
        job_id = orch.submit(robot)
        return {"job_id": job_id.value}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/cancel-job/{job_id}")
async def cancel_job(job_id: int) -> dict[str, str]:
    """Cancel a running job."""
    orch = get_orchestrator()
    try:
        orch.cancel(JobId(job_id))
        return {"status": "cancelled"}
    except JobNotFound as exc:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found") from exc
    except JobAlreadyFinished as exc:
        raise HTTPException(
            status_code=409, detail=f"Job {job_id} already finished"
        ) from exc


@app.get("/job/{job_id}")
async def get_job(job_id: int) -> dict[str, Any]:
    """Get job status and report."""
    orch = get_orchestrator()
    job = orch.get(JobId(job_id))
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {
        "id": job.id.value,
        "robot_name": job.robot_name,
        "status": job.status.value,
        "report": _serialize_report(job.report),
    }


@app.get("/history")
async def get_history() -> list[dict[str, Any]]:
    """Get all jobs sorted by ID."""
    orch = get_orchestrator()
    jobs = orch.history()
    return [
        {
            "id": job.id.value,
            "robot_name": job.robot_name,
            "status": job.status.value,
        }
        for job in jobs
    ]


@app.get("/context/{job_id}")
async def get_context(job_id: int) -> dict[str, Any]:
    """Get context variables for a job."""
    orch = get_orchestrator()
    snap = orch.context_snapshot(JobId(job_id))
    return snap


@app.post("/save-file")
async def save_file(req: SaveFileRequest) -> dict[str, str]:
    """Save a robot JSON file."""
    try:
        import json

        # Validate it's valid JSON
        json.loads(req.content)
        with open(req.path, "w", encoding="utf-8") as f:
            f.write(req.content)
        return {"status": "saved", "path": req.path}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/run-debug")
async def run_debug(req: RunDebugRequest) -> dict[str, Any]:
    """Submit a robot in debug mode (paused at first step)."""
    try:
        robot = Robot(**req.robot)
        orch = get_orchestrator()
        job_id = orch.submit_debug(robot, set(req.breakpoints))
        return {"job_id": job_id.value}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/set-breakpoints/{job_id}")
async def set_breakpoints(job_id: int, req: SetBreakpointsRequest) -> dict[str, str]:
    """Set breakpoints for a debug job."""
    # TODO: integrate with DebugController
    return {"status": "ok"}


@app.post("/resume/{job_id}")
async def resume_execution(job_id: int) -> dict[str, str]:
    """Resume a paused debug job."""
    orch = get_orchestrator()
    with contextlib.suppress(JobNotFound, KeyError):
        orch.resume(JobId(job_id))
    return {"status": "resumed"}


@app.post("/step-over/{job_id}")
async def step_over(job_id: int) -> dict[str, str]:
    """Step over in debug mode."""
    orch = get_orchestrator()
    with contextlib.suppress(JobNotFound, KeyError):
        orch.step_over(JobId(job_id))
    return {"status": "step_over"}


@app.get("/debug-status/{job_id}")
async def debug_status(job_id: int) -> dict[str, Any]:
    """Get debug status for a job."""
    orch = get_orchestrator()
    step = orch.current_step(JobId(job_id))
    paused = orch.is_paused(JobId(job_id))
    if step is None and paused is None:
        return {"current_step": 0, "is_paused": False}
    return {"current_step": step or 0, "is_paused": paused or False}


def _serialize_report(report: Any) -> Any:
    """Serialize an ExecutionReport for JSON response."""
    if report is None:
        return None
    if hasattr(report, "ok"):
        return {
            "ok": report.ok,
            "robot_name": report.robot_name,
            "duration_ms": report.duration_ms,
            "steps": [
                {
                    "step_index": s.step_index,
                    "action": s.action,
                    "ok": s.ok,
                    "output": s.output,
                    "error": str(s.error) if s.error else None,
                }
                for s in report.steps
            ],
        }
    return str(report)
