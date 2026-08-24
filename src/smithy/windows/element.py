"""SafeUIElement — thread-safe wrapper around a UIA element."""

from __future__ import annotations

import asyncio
from typing import Any


class SafeUIElement:
    """Thread-safe wrapper around a UIA element.

    UIA elements are COM objects and not thread-safe. This wrapper
    runs UIA operations in a thread executor to avoid blocking the
    asyncio event loop.
    """

    def __init__(self, element: Any) -> None:
        self._element = element

    @property
    def element(self) -> Any:
        """Access the underlying UIA element (not thread-safe)."""
        return self._element

    async def click(self) -> None:
        """Click the element (runs in thread executor)."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._element.Click)

    async def get_name(self) -> str:
        """Get the element's name."""
        loop = asyncio.get_running_loop()
        return str(await loop.run_in_executor(None, self._element.Name))

    async def get_control_type(self) -> str:
        """Get the element's control type."""
        loop = asyncio.get_running_loop()
        return str(await loop.run_in_executor(None, self._element.ControlTypeName))

    async def get_automation_id(self) -> str:
        """Get the element's automation ID."""
        loop = asyncio.get_running_loop()
        return str(await loop.run_in_executor(None, self._element.AutomationId))
