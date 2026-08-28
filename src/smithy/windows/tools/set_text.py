"""SetTextTool — replace the text of a Windows UI element."""

from __future__ import annotations

from typing import Any

from smithy.core.context import ExecutionContext
from smithy.core.errors import ElementNotFound, InvalidInput
from smithy.core.tool import AbstractTool
from smithy.windows.tools._resolve import resolve_element


class SetTextTool(AbstractTool):
    """Set an element's value via the UIA ValuePattern (replaces text)."""

    @property
    def name(self) -> str:
        return "windows.set_text"

    @property
    def description(self) -> str:
        return (
            "Sets the text of a UI element via the UIA ValuePattern. "
            "Use to replace an input field's entire value."
        )

    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to set"},
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

        # uiautomation sets the value via IValueProvider when available,
        # and falls back to SetFocus + Ctrl+A + SendKeys otherwise.
        element.SetValue(text)
        return {"status": "set", "text": text}