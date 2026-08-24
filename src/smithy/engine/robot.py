"""Robot and Step Pydantic models — JSON robot definition."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Step(BaseModel):
    """A single step in a robot execution plan."""

    action: str
    params: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, str] | None = None
    stop_on_error: bool = True


class Robot(BaseModel):
    """A robot — named sequence of steps loaded from JSON."""

    name: str
    version: str
    steps: list[Step]
