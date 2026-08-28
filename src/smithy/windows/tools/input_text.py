"""InputTool — type text into a Windows UI element."""

from __future__ import annotations

import asyncio
from typing import Any

from smithy.core.context import ExecutionContext
from smithy.core.errors import ElementNotFound, InvalidInput
from smithy.core.tool import AbstractTool
from smithy.windows.tools._resolve import resolve_element


class InputTool(AbstractTool):
    """Type text into a UI element (focuses it, then sends keystrokes)."""

    @property
    def name(self) -> str:
        return "windows.input_text"

    @property
    def description(self) -> str:
        return (
            "Types text into a UI element by focusing it and sending "
            "keystrokes. Use for appending text into an input field."
        )

    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to type"},
                "element_key": {
                    "type": "string",
                    "description": "Key in context with UIElement",
                },
                "name": {"type": "string", "description": "Element name to find"},
                "automation_id": {
                    "type": "string",
                    "description": "UI Automation identifier",
                },
                "control_type": {
                    "type": "string",
                    "description": "Control type",
                },
                "class_name": {"type": "string", "description": "Window class name"},
                "pid": {"type": "integer", "description": "Process ID filter"},
            },
            "required": ["text"],
        }

    async def execute(
        self,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> Any:
        text = config.get("text")
        if text is None:
            raise InvalidInput("Missing required parameter: text", param="text")

        element = await resolve_element(config, ctx)
        if element is None:
            raise ElementNotFound(
                "No element found: provide element_key or selector fields",
                selector=config,
            )

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, element.SetFocus)
        await loop.run_in_executor(None, element.SendKeys, text)

        return {"status": "typed", "text": text}