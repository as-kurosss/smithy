"""Shared helpers for resolving a UI element from a tool config."""

from __future__ import annotations

import asyncio
from typing import Any

from smithy.core.errors import InvalidInput
from smithy.windows.selector import ElementSelector, _parse_control_type


def build_selector(config: dict[str, Any]) -> ElementSelector | None:
    """Build a selector from inline config fields, or None if none are present."""
    keys = ("name", "automation_id", "control_type", "class_name", "pid")
    if not any(k in config for k in keys):
        return None

    if "pid" in config:
        pid = config["pid"]
        if isinstance(pid, bool) or not isinstance(pid, int):
            raise InvalidInput(
                "Invalid 'pid': expected an integer",
                param="pid",
                input_value=pid,
            )
    if "control_type" in config:
        raw_ct = config["control_type"]
        if not isinstance(raw_ct, str) or _parse_control_type(raw_ct) is None:
            raise InvalidInput(
                f"Unknown control_type: {raw_ct!r}",
                param="control_type",
                input_value=raw_ct,
            )
    selector = ElementSelector()
    if "name" in config:
        selector = selector.with_name(config["name"])
    if "automation_id" in config:
        selector = selector.with_automation_id(config["automation_id"])
    if "control_type" in config:
        selector = selector.with_control_type(config["control_type"])
    if "class_name" in config:
        selector = selector.with_class_name(config["class_name"])
    if "pid" in config:
        selector = selector.with_pid(config["pid"])
    return selector


async def resolve_element(config: dict[str, Any]) -> Any:
    """Resolve a UI element from inline selector fields.

    Returns:
        A raw ``uiautomation`` control, or ``None`` if no selector
        fields were given.

    Raises:
        InvalidInput: If ``element_key`` is used — context-based lookup
            is not implemented; use inline selector fields instead.
    """
    if "element_key" in config:
        raise InvalidInput(
            "element_key is not supported: pass inline selector fields "
            "(name, automation_id, control_type, class_name, pid) instead",
            param="element_key",
            input_value=config.get("element_key"),
        )
    selector = build_selector(config)
    if selector is None:
        return None

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, selector.find_from_desktop)
