"""CLI — validate and run robot JSON files."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from smithy.engine.robot import Robot
from smithy.engine.tools import default_registry
from smithy.orchestrator.orchestrator import Orchestrator


def main(argv: list[str] | None = None) -> None:
    """Entry point for the smithy CLI."""
    parser = argparse.ArgumentParser(
        prog="smithy",
        description="Smithy — Python RPA engine CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # validate
    val = sub.add_parser("validate", help="Validate a robot JSON file")
    val.add_argument("file", type=Path, help="Path to robot JSON file")

    # run
    run = sub.add_parser("run", help="Run a robot from a JSON file")
    run.add_argument("file", type=Path, help="Path to robot JSON file")

    args = parser.parse_args(argv)

    if args.command == "validate":
        cmd_validate(args.file)
    elif args.command == "run":
        asyncio.run(cmd_run(args.file))


def cmd_validate(path: Path) -> None:
    """Validate a robot JSON file."""
    try:
        raw = path.read_text(encoding="utf-8")
        robot = Robot.model_validate_json(raw)
        print(f"OK — {robot.name} v{robot.version}, {len(robot.steps)} steps")
    except Exception as exc:
        print(f"FAIL — {exc}", file=sys.stderr)
        sys.exit(1)


async def cmd_run(path: Path) -> None:
    """Run a robot from a JSON file."""
    try:
        raw = path.read_text(encoding="utf-8")
        robot = Robot.model_validate_json(raw)
    except Exception as exc:
        print(f"FAIL — {exc}", file=sys.stderr)
        sys.exit(1)

    registry = default_registry()
    orch = Orchestrator(registry)
    job_id = orch.submit(robot)

    # Wait for completion
    while True:
        job = orch.get(job_id)
        if job is None:
            break
        status = job.status.value
        if status in ("succeeded", "failed", "cancelled"):
            break
        await asyncio.sleep(0.1)

    job = orch.get(job_id)
    if job is None:
        print("Job disappeared", file=sys.stderr)
        sys.exit(1)

    if job.status.value == "succeeded":
        if job.report:
            print(f"OK — {job.robot_name} completed in {job.report.duration_ms:.0f}ms")
        else:
            print(f"OK — {job.robot_name} completed")
    else:
        print(f"FAIL — {job.status.value}", file=sys.stderr)
        if job.report and job.report.steps:
            for step in job.report.steps:
                if step.error:
                    print(f"  Step {step.step_index} ({step.action}): {step.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
