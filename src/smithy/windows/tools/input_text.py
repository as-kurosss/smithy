"""InputTextTool — type text and/or send key combinations."""

from __future__ import annotations

import asyncio
import re
from typing import Any

from smithy.core.context import ExecutionContext
from smithy.core.errors import InvalidInput
from smithy.core.tool import AbstractTool
from smithy.windows.tools._resolve import resolve_element

# Detects SheRPA-style hold/release: [+CTRL], [-CTRL], [CTRL].
_SHERPA_RE = re.compile(r"\[([+-]?)(\w+)\]")


def normalize_input(text: str) -> str:
    """Normalize user input for ``uiautomation.SendKeys``.

    Bracketed tokens are key presses; everything else is literal text.

    Examples:
    - ``"Hello World"``          → ``"Hello World"``
    - ``"[CTRL]"``               → ``"{CTRL}"``
    - ``"[+CTRL][S][-CTRL]"``    → ``"{+CTRL}S{-CTRL}"``
    - ``"Hello [CTRL]"``         → ``"Hello {CTRL}"``
    """
    if "[" not in text:
        return text

    def _replace(m: re.Match[str]) -> str:
        sign, key = m.group(1), m.group(2)
        key_upper = key.upper()
        if sign == "+":
            return "{+" + key_upper + "}"
        if sign == "-":
            return "{-" + key_upper + "}"
        return "{" + key_upper + "}"

    return _SHERPA_RE.sub(_replace, text)


def _send(text: str) -> None:
    """Send keystrokes via uiautomation."""
    import uiautomation as auto

    auto.SendKeys(text)


class InputTextTool(AbstractTool):
    """Type text and/or send key combinations.

    Can work with or without a target element:
    - With element: focuses it first, then sends input.
    - Without element: sends input to the currently focused window.

    Bracketed tokens are key presses; everything else is literal text.

    Examples:
    - ``"Hello World"``          — type plain text
    - ``"[CTRL]"``               — press Ctrl
    - ``"[+CTRL][S][-CTRL]"``    — hold Ctrl, press S, release
    - ``"Hello [CTRL]"``         — type "Hello ", then press Ctrl
    - ``"CTRL"`` (no brackets)   — type literal "CTRL"
    """

    @property
    def name(self) -> str:
        return "windows.input_text"

    @property
    def description(self) -> str:
        return (
            "Types text and/or sends key combinations to a UI element "
            "or the focused window"
        )

    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": (
                        "Text and/or key presses. Bracketed tokens are "
                        "keys: '[CTRL]', '[+CTRL][S][-CTRL]'. "
                        "Everything else is literal text."
                    ),
                },
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
        raw = config.get("text")
        if not raw:
            raise InvalidInput("Missing required parameter: text", param="text")

        keys = normalize_input(raw)
        loop = asyncio.get_running_loop()

        # Focus element first if one was resolved.
        element = await resolve_element(config, ctx)
        if element is not None:
            await loop.run_in_executor(None, element.SetFocus)

        await loop.run_in_executor(None, _send, keys)
        return {"status": "sent", "text": raw, "normalized": keys}
