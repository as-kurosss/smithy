"""Retry policy for RPA steps."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetryPolicy:
    """Retry configuration for a step.

    Attributes:
        max_retries: Maximum number of retries (0 = no retries).
        delay_ms: Delay between retries in milliseconds.
    """

    max_retries: int = 0
    delay_ms: int = 0
