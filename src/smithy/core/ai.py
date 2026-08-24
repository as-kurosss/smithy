"""AiHandler — abstraction over LLM agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from smithy.core.context import ExecutionContext


class AiHandler(ABC):
    """Trait for handling AI steps.

    Implemented by SmithAgent or any other LLM agent.
    """

    @abstractmethod
    async def agent_run(
        self,
        prompt: str,
        tools: list[str],
        max_steps: int,
        ctx: ExecutionContext,
    ) -> Any:
        """Execute a prompt with tools (ReAct loop)."""
        ...

    @abstractmethod
    async def think(
        self,
        prompt: str,
        schema: dict[str, Any],
        ctx: ExecutionContext,
    ) -> Any:
        """Execute think (LLM without tools, data generation)."""
        ...

    @abstractmethod
    async def decide(
        self,
        prompt: str,
        options: list[str],
        ctx: ExecutionContext,
    ) -> str:
        """Execute decide (LLM selects an option from a list)."""
        ...
