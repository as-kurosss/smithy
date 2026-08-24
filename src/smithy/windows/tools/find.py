"""FindTool — find a Windows UI element and store it in context."""

from __future__ import annotations

from typing import Any

from smithy.core.context import ExecutionContext
from smithy.core.errors import ElementNotFound, InvalidInput
from smithy.core.tool import AbstractTool
from smithy.windows.selector import ElementSelector


class FindTool(AbstractTool):
    """Find a Windows UI element matching selectors and store in context."""

    @property
    def name(self) -> str:
        return "windows.find"

    @property
    def description(self) -> str:
        return (
            "Finds a Windows UI element matching the specified "
            "selectors and stores it in context"
        )

    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Element name to match",
                },
                "automation_id": {
                    "type": "string",
                    "description": "UI Automation identifier",
                },
                "control_type": {
                    "type": "string",
                    "description": "Control type",
                },
                "class_name": {
                    "type": "string",
                    "description": "Window class name",
                },
                "pid": {
                    "type": "integer",
                    "description": "Process ID filter",
                },
                "output_key": {
                    "type": "string",
                    "description": "Key to store element in context",
                },
                "delay_before_ms": {"type": "integer", "minimum": 0},
                "delay_after_ms": {"type": "integer", "minimum": 0},
            },
            "required": ["output_key"],
        }

    async def execute(
        self,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> Any:
        output_key = config.get("output_key")
        if not output_key:
            raise InvalidInput("Missing required parameter: output_key", param="output_key")

        # Build selector from input
        selector = ElementSelector()
        if "name" in config:
            selector.with_name(config["name"])
        if "automation_id" in config:
            selector.with_automation_id(config["automation_id"])
        if "control_type" in config:
            selector.with_control_type(config["control_type"])
        if "class_name" in config:
            selector.with_class_name(config["class_name"])
        if "pid" in config:
            selector.with_pid(config["pid"])

        # Find element (runs in thread executor to avoid blocking)
        import asyncio

        loop = asyncio.get_running_loop()
        try:
            element = await loop.run_in_executor(None, selector.find_from_desktop)
        except ElementNotFound:
            raise
        except Exception as exc:
            from smithy.core.errors import PlatformError

            raise PlatformError(
                "Find element failed",
                source=exc,
            ) from exc

        # Store in context
        ctx.set(output_key, element)

        return {"status": "found"}
