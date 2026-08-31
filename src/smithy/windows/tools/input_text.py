"""InputTextTool — type text and/or send key combinations."""

from __future__ import annotations

import asyncio
import re
from typing import Any

from smithy.core.context import ExecutionContext
from smithy.core.errors import InvalidInput
from smithy.core.tool import AbstractTool
from smithy.windows.tools._resolve import resolve_element

# Maps user-friendly key names to uiautomation key strings.
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
    "f1": "{F1}", "f2": "{F2}", "f3": "{F3}", "f4": "{F4}",
    "f5": "{F5}", "f6": "{F6}", "f7": "{F7}", "f8": "{F8}",
    "f9": "{F9}", "f10": "{F10}", "f11": "{F11}", "f12": "{F12}",
    "num0": "{NUMPAD0}", "num1": "{NUMPAD1}", "num2": "{NUMPAD2}",
    "num3": "{NUMPAD3}", "num4": "{NUMPAD4}", "num5": "{NUMPAD5}",
    "num6": "{NUMPAD6}", "num7": "{NUMPAD7}", "num8": "{NUMPAD8}",
    "num9": "{NUMPAD9}",
}

# Detects SheRPA-style hold/release: [+CTRL], [-CTRL], [CTRL].
_SHERPA_RE = re.compile(r"\[([+-]?)(\w+)\]")


def _normalize_modifier_combo(segment: str) -> str:
    """Normalize ``ctrl+s`` → ``{CTRL}s`` and ``ctrl+shift+s`` → ``{CTRL}{SHIFT}s``."""
    parts = [p.strip().lower() for p in segment.split("+")]
    if len(parts) == 1:
        alias = _KEY_ALIASES.get(parts[0])
        return alias if alias is not None else segment
    out: list[str] = []
    for part in parts:
        alias = _KEY_ALIASES.get(part)
        out.append(alias if alias is not None else part)
    return "".join(out)


def normalize_input(text: str) -> str:
    """Normalize user input for ``uiautomation.SendKeys``.

    Handles three formats:
    1. SheRPA hold/release: ``[+CTRL]S[-CTRL]`` → ``{+CTRL}S{-CTRL}``
    2. Modifier combos:    ``CTRL+S``          → ``{CTRL}s``
    3. Plain text:         ``Hello World``     → ``Hello World`` (unchanged)
    """
    # 1. SheRPA-style [+MOD] / [-MOD] / [MOD].
    if "[" in text:

        def _replace(m: re.Match[str]) -> str:
            sign, key = m.group(1), m.group(2)
            key_upper = key.upper()
            if sign == "+":
                return "{+" + key_upper + "}"
            if sign == "-":
                return "{-" + key_upper + "}"
            return "{" + key_upper + "}"

        return _SHERPA_RE.sub(_replace, text)

    # 2. Check if the entire input is a modifier combo like CTRL+S.
    #    Heuristic: contains '+', and every segment is a known key name
    #    or a single character (letter/digit) — so "hello world" won't
    #    be treated as a combo, but "CTRL+S" will.
    if "+" in text:
        segments = [s.strip() for s in text.split("+")]
        if all(s.lower() in _KEY_ALIASES or len(s) == 1 for s in segments):
            return _normalize_modifier_combo(text)

    # 3. Single bare key name (e.g. "enter", "esc", "f1").
    alias = _KEY_ALIASES.get(text.lower())
    if alias is not None:
        return alias

    # 4. Plain text — pass through unchanged.
    return text


def _send(text: str) -> None:
    """Send keystrokes via uiautomation."""
    import uiautomation as auto

    auto.SendKeys(text)


class InputTextTool(AbstractTool):
    """Type text and/or send key combinations.

    Can work with or without a target element:
    - With element: focuses it first, then sends input.
    - Without element: sends input to the currently focused window.

    Supported input formats:
    - Plain text:       ``"Hello World"``
    - Key combination:  ``"CTRL+S"``, ``"ALT+F4"``
    - Mixed:            ``"Hello CTRL+S"``
    - Hold/release:     ``"[+CTRL]A[-CTRL]"``
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
                        "Text, key combination, or mixed input, "
                        "e.g. 'Hello', 'CTRL+S', 'Hello CTRL+S', "
                        "'[+CTRL]A[-CTRL]'"
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
