"""KeyboardTool — send key presses and combinations."""

from __future__ import annotations

import asyncio
from typing import Any

from smithy.core.context import ExecutionContext
from smithy.core.errors import InvalidInput
from smithy.core.tool import AbstractTool

# Normalize simple aliases to uiautomation key strings.
_KEY_ALIASES: dict[str, str] = {
    "esc": "{ESC}",
    "escape": "{ESC}",
    "enter": "{ENTER}",
    "return": "{ENTER}",
    "tab": "{TAB}",
    "space": " ",
    "backspace": "{BACKSPACE}",
    "delete": "{DELETE}",
    "del": "{DELETE}",
    "up": "{UP}",
    "down": "{DOWN}",
    "left": "{LEFT}",
    "right": "{RIGHT}",
    "home": "{HOME}",
    "end": "{END}",
    "pageup": "{PAGEUP}",
    "pgup": "{PAGEUP}",
    "pagedown": "{PAGEDOWN}",
    "pgdn": "{PAGEDOWN}",
    "insert": "{INSERT}",
    "ins": "{INSERT}",
    "ctrl": "{CTRL}",
    "control": "{CTRL}",
    "shift": "{SHIFT}",
    "alt": "{ALT}",
    "win": "{WIN}",
    "lwin": "{LWIN}",
    "rwin": "{RWIN}",
    "capslock": "{CAPSLOCK}",
    "numlock": "{NUMLOCK}",
    "scrolllock": "{SCROLLLOCK}",
    "printscreen": "{PRTSC}",
    "prtsc": "{PRTSC}",
    "f1": "{F1}",
    "f2": "{F2}",
    "f3": "{F3}",
    "f4": "{F4}",
    "f5": "{F5}",
    "f6": "{F6}",
    "f7": "{F7}",
    "f8": "{F8}",
    "f9": "{F9}",
    "f10": "{F10}",
    "f11": "{F11}",
    "f12": "{F12}",
    "num0": "{NUMPAD0}",
    "num1": "{NUMPAD1}",
    "num2": "{NUMPAD2}",
    "num3": "{NUMPAD3}",
    "num4": "{NUMPAD4}",
    "num5": "{NUMPAD5}",
    "num6": "{NUMPAD6}",
    "num7": "{NUMPAD7}",
    "num8": "{NUMPAD8}",
    "num9": "{NUMPAD9}",
}


def normalize_keys(keys: str) -> str:
    """Normalize a user-supplied key expression.

    Supports:
    - ``"ctrl+s"`` / ``"ctrl+shift+s"`` → ``{CTRL}s`` / ``{CTRL}{SHIFT}s``
    - bare names like ``"enter"`` / ``"esc"``
    - ``+`` joins modifiers; ``^`` / ``%`` are not special-cased.
    """
    parts = [p.strip().lower() for p in keys.split("+")]
    if len(parts) == 1:
        alias = _KEY_ALIASES.get(parts[0])
        return alias if alias is not None else keys

    out: list[str] = []
    for part in parts:
        alias = _KEY_ALIASES.get(part)
        out.append(alias if alias is not None else part)
    return "".join(out)


class KeyboardTool(AbstractTool):
    """Send key presses and keyboard combinations."""

    @property
    def name(self) -> str:
        return "windows.keyboard"

    @property
    def description(self) -> str:
        return (
            "Sends key presses and combinations (e.g. ctrl+s, enter, tab, "
            "alt+f4) to the focused window"
        )

    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "keys": {
                    "type": "string",
                    "description": (
                        "Key or combination, e.g. 'enter', 'ctrl+s', "
                        "'alt+f4'"
                    ),
                },
            },
            "required": ["keys"],
        }

    async def execute(
        self,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> Any:
        raw = config.get("keys")
        if not raw:
            raise InvalidInput("Missing required parameter: keys", param="keys")

        keys = normalize_keys(raw)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _send_keys, keys)

        return {"status": "sent", "keys": keys}


def _send_keys(keys: str) -> None:
    """Send keystrokes to the currently focused window."""
    import uiautomation as auto

    auto.SendKeys(keys)