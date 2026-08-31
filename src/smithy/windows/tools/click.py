"""ClickTool — click a Windows UI element."""

from __future__ import annotations

import asyncio
from typing import Any

from smithy.core.errors import ElementNotFound, PlatformError
from smithy.core.tool import AbstractTool
from smithy.windows.element import SafeUIElement
from smithy.windows.tools._resolve import resolve_element


class ClickTool(AbstractTool):
    """Perform a click on a UI element by context key or inline selector."""

    @property
    def name(self) -> str:
        return "windows.click"

    @property
    def description(self) -> str:
        return "Performs a click on a UI element by context key or inline selector"

    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "element_key": {
                    "type": "string",
                    "description": "Key in context with UIElement",
                },
                "name": {
                    "type": "string",
                    "description": "Element name to find",
                },
                "automation_id": {
                    "type": "string",
                    "description": "UI Automation identifier",
                },
                "control_type": {
                    "type": "string",
                    "description": "Control type",
                },
                "class_name": {"type": "string", "description": "Window class name"},
                "pid": {
                    "type": "integer",
                    "description": "Process ID filter",
                },
            },
            "required": [],
        }

    async def execute(
        self,
        config: dict[str, Any],
    ) -> Any:
        element = await resolve_element(config)
        if element is None:
            raise ElementNotFound(
                "No element found: provide element_key or selector fields",
                selector=config,
            )

        if isinstance(element, SafeUIElement):
            await element.click()
        else:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, element.Click)

        return {"status": "clicked"}

