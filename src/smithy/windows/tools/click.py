"""ClickTool — click a Windows UI element."""

from __future__ import annotations

import asyncio
from typing import Any

from smithy.core.context import ExecutionContext
from smithy.core.errors import ElementNotFound
from smithy.core.tool import AbstractTool
from smithy.windows.element import SafeUIElement
from smithy.windows.selector import ElementSelector


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
                "delay_before_ms": {"type": "integer", "minimum": 0},
                "delay_after_ms": {"type": "integer", "minimum": 0},
            },
            "required": [],
        }

    async def execute(
        self,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> Any:
        # Optional delay before
        delay_before = config.get("delay_before_ms", 0)
        if delay_before and delay_before > 0:
            await asyncio.sleep(delay_before / 1000)

        # Resolve element from context key or inline selector
        element = await _resolve_element(config, ctx)
        if element is None:
            raise ElementNotFound(
                "No element found: provide element_key or selector fields",
                selector=config,
            )

        # Click
        if isinstance(element, SafeUIElement):
            await element.click()
        else:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, element.Click)

        # Optional delay after
        delay_after = config.get("delay_after_ms", 0)
        if delay_after and delay_after > 0:
            await asyncio.sleep(delay_after / 1000)

        return {"status": "clicked"}


async def _resolve_element(
    config: dict[str, Any],
    ctx: ExecutionContext,
) -> Any:
    """Resolve element from context key or inline selector."""
    element_key = config.get("element_key")
    if element_key:
        cv = ctx.get(element_key)
        if cv is None:
            return None
        val = cv.value
        if isinstance(val, SafeUIElement):
            return val
        return val

    # Build selector from inline fields
    selector = ElementSelector()
    if "name" in config:
        selector.with_name(config["name"])
    if "automation_id" in config:
        selector.with_automation_id(config["automation_id"])
    if "control_type" in config:
        selector.with_control_type(config["control_type"])
    if "class_name" in config:
        selector.with_class_name(config["class_name"])

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, selector.find_from_desktop)
