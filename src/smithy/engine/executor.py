"""RobotExecutor — executes a Robot step by step."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from smithy.core.context import ExecutionContext
from smithy.core.errors import ToolError
from smithy.core.registry import ToolRegistry
from smithy.engine.interpolate import interpolate_value
from smithy.engine.robot import Robot


@dataclass
class StepResult:
    """Result of a single step execution."""

    step_index: int
    action: str
    output: Any = None
    error: ToolError | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class ExecutionReport:
    """Report after a full robot execution."""

    robot_name: str
    steps: list[StepResult]
    duration_ms: float

    @property
    def ok(self) -> bool:
        return all(s.ok for s in self.steps)


class RobotExecutor:
    """Executes a Robot against a ToolRegistry with shared context."""

    def __init__(
        self,
        registry: ToolRegistry,
        ctx: ExecutionContext,
    ) -> None:
        self._registry = registry
        self._ctx = ctx

    async def execute(self, robot: Robot) -> ExecutionReport:
        """Run all steps in the robot sequentially.

        If a step has ``stop_on_error=True`` and fails, execution halts.
        Step outputs are written into the context via the ``outputs`` mapping.
        """
        t0 = time.perf_counter()
        results: list[StepResult] = []

        for idx, step in enumerate(robot.steps):
            try:
                config = interpolate_value(step.params, self._ctx)
                output = await self._registry.execute(step.action, config, self._ctx)

                # Store outputs in context
                if step.outputs:
                    for ctx_key, ctx_var in step.outputs.items():
                        # The output value may be a nested key or the whole output
                        if isinstance(output, dict) and ctx_key in output:
                            self._ctx.set(ctx_var, output[ctx_key])
                        elif isinstance(output, dict) and ctx_key not in output:
                            self._ctx.set(ctx_var, output)
                        else:
                            self._ctx.set(ctx_var, output)

                results.append(StepResult(step_index=idx, action=step.action, output=output))

            except ToolError as exc:
                results.append(StepResult(step_index=idx, action=step.action, error=exc))
                if step.stop_on_error:
                    break

        elapsed = (time.perf_counter() - t0) * 1000
        return ExecutionReport(robot_name=robot.name, steps=results, duration_ms=elapsed)
