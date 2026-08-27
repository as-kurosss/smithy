"""DebugController — step-by-step debugging with breakpoints."""

from __future__ import annotations

import asyncio
from enum import StrEnum


class StepAction(StrEnum):
    """Decision for the executor loop."""

    EXECUTE = "execute"
    PAUSE = "pause"


class DebugController:
    """Shared controller linking executor loop with external API.

    Uses ``asyncio.Event`` for safe cross-coroutine signaling.
    """

    def __init__(self) -> None:
        self._breakpoints: set[int] = set()
        self._current_step: int = 0
        self._paused: bool = False
        self._pause_after_step: bool = False
        self._resume_event: asyncio.Event = asyncio.Event()

    async def set_breakpoints(self, points: set[int]) -> None:
        """Replace all breakpoints."""
        self._breakpoints = points.copy()

    async def add_breakpoint(self, index: int) -> None:
        """Add a single breakpoint."""
        self._breakpoints.add(index)

    async def remove_breakpoint(self, index: int) -> None:
        """Remove a single breakpoint."""
        self._breakpoints.discard(index)

    async def should_continue(self, step_index: int) -> StepAction:
        """Check if execution should continue or pause at this step.

        If paused, waits for resume/step_over signal via the event.
        """
        if self._paused:
            if self._resume_event.is_set():
                self._resume_event.clear()
                self._paused = False
                return StepAction.EXECUTE
            await self._resume_event.wait()
            self._resume_event.clear()
            self._paused = False
            return StepAction.PAUSE

        if step_index in self._breakpoints:
            self._paused = True
            await self._resume_event.wait()
            self._resume_event.clear()
            self._paused = False
            return StepAction.PAUSE

        return StepAction.EXECUTE

    def update_step(self, index: int) -> None:
        """Update current step index."""
        self._current_step = index

    def check_step_over(self) -> bool:
        """Check if pause_after_step flag is set. If so, pause."""
        if self._pause_after_step:
            self._pause_after_step = False
            self._paused = True
            return True
        return False

    def continue_execution(self) -> None:
        """Resume execution: signal the event to wake the executor."""
        self._resume_event.set()

    def step_over(self) -> None:
        """Resume and pause after next step."""
        self._pause_after_step = True
        self._resume_event.set()

    def current_step(self) -> int:
        """Return current step index."""
        return self._current_step

    def is_paused(self) -> bool:
        """Return True if paused."""
        return self._paused

    def set_pause_after_step(self, value: bool) -> None:
        """Set pause_after_step flag."""
        self._pause_after_step = value

    async def wait_for_resume(self) -> None:
        """Wait for resume signal from the API (resume/step_over)."""
        await self._resume_event.wait()
        self._resume_event.clear()

