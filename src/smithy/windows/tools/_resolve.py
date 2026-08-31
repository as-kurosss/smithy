"""Shared helpers for resolving a UI element from a tool config."""

from __future__ import annotations

import asyncio
from typing import Any
from smithy.windows.selector import ElementSelector


def build_selector(config: dict[str, Any]) -> ElementSelector | None:
    """Build a selector from inline config fields, or None if none are present."""
    keys = ("name", "automation_id", "control_type", "class_name", "pid")
    if not any(k in config for k in keys):
        return None

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
    return selector


async def resolve_element(config: dict[str, Any]) -> Any:
    """Resolve a UI element from inline selector fields.

    Returns:
        A raw ``uiautomation`` control, or ``None`` if no selector
        fields were given.
    """
    selector = build_selector(config)
    if selector is None:
        return None

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, selector.find_from_desktop)
