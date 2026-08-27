"""Config generation per tool type.

Takes a captured ``BestSelector`` and produces the JSON config dict
that the corresponding ``smithy.windows.tools`` tool expects.

Ported from ``selector-capture/src/generate.rs``.
"""

from __future__ import annotations

import enum
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from smithy.windows.tools.selector_capture.capture import BestSelector


class ToolType(enum.StrEnum):
    """Target tool type for config generation.

    Attributes:
        FIND: Locate an element via selectors.
        CLICK: Click an element found by a preceding find step.
        INPUT_TEXT: Append text into an input element.
        SET_TEXT: Replace text in an input element.
        WAIT: Pause execution for a fixed duration.
    """

    FIND = "find"
    CLICK = "click"
    INPUT_TEXT = "input_text"
    SET_TEXT = "set_text"
    WAIT = "wait"

    # -- helpers (ported from Rust ToolType impl) --

    @property
    def needs_text(self) -> bool:
        """Return ``True`` if this tool type requires a *text* parameter."""
        return self in (ToolType.INPUT_TEXT, ToolType.SET_TEXT)

    @property
    def needs_duration(self) -> bool:
        """Return ``True`` if this tool type requires a *duration_ms* parameter."""
        return self is ToolType.WAIT

    @property
    def needs_element_key(self) -> bool:
        """Return ``True`` if this tool type depends on a preceding find step."""
        return self in (ToolType.CLICK, ToolType.INPUT_TEXT, ToolType.SET_TEXT)

    @property
    def generates_two_nodes(self) -> bool:
        """Return ``True`` if this tool produces a find + action node pair."""
        return self in (ToolType.CLICK, ToolType.INPUT_TEXT, ToolType.SET_TEXT)


@dataclass(frozen=True, slots=True)
class GenerateParams:
    """Parameters for generating tool configs.

    Attributes:
        output_key: Auto-generated output key for the find step.
        text: Text for ``input_text`` / ``set_text`` tools.
        duration_ms: Duration (milliseconds) for the ``wait`` tool.
    """

    output_key: str
    text: str = ""
    duration_ms: int = 1000


@dataclass(frozen=True, slots=True)
class FlowNode:
    """A single node in a generated flow.

    Attributes:
        tool: Fully-qualified tool name (e.g. ``windows.find``).
        args: Configuration dictionary the tool expects.
        full_path: Complete UIA element path from desktop root to the target.
    """
    tool: str
    args: Mapping[str, object] = field(default_factory=dict)
    full_path: Sequence[Mapping[str, object]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_nodes(
    selector: BestSelector,
    tool: ToolType,
    params: GenerateParams,
) -> list[FlowNode]:
    """Generate one or two :class:`FlowNode` objects for a captured element.

    Mapping:
        * ``Find``  → ``[windows.find]``
        * ``Click`` → ``[windows.find, windows.click]``
        * ``InputText`` → ``[windows.find, windows.input_text]``
        * ``SetText`` → ``[windows.find, windows.set_text]``
        * ``Wait`` → ``[windows.wait]``

    Args:
        selector: The best-effort selector captured from a UI element.
        tool: The target tool type.
        params: Generation parameters (output key, text, duration).

    Returns:
        A list of :class:`FlowNode` objects forming the tool sequence.
    """
    match tool:
        case ToolType.FIND:
            return [
                FlowNode(
                    tool="windows.find",
                    args=build_find_config(selector, params.output_key),
                ),
            ]
        case ToolType.CLICK:
            return [
                FlowNode(
                    tool="windows.find",
                    args=build_find_config(selector, params.output_key),
                ),
                FlowNode(
                    tool="windows.click",
                    args=build_click_config(params.output_key),
                ),
            ]
        case ToolType.INPUT_TEXT:
            return [
                FlowNode(
                    tool="windows.find",
                    args=build_find_config(selector, params.output_key),
                ),
                FlowNode(
                    tool="windows.input_text",
                    args=build_text_config(params.text, params.output_key),
                ),
            ]
        case ToolType.SET_TEXT:
            return [
                FlowNode(
                    tool="windows.find",
                    args=build_find_config(selector, params.output_key),
                ),
                FlowNode(
                    tool="windows.set_text",
                    args=build_text_config(params.text, params.output_key),
                ),
            ]
        case ToolType.WAIT:
            return [
                FlowNode(
                    tool="windows.wait",
                    args=build_wait_config(params.duration_ms),
                ),
            ]


def generate_action_config(
    selector: BestSelector,
    tool: ToolType,
    params: GenerateParams,
) -> Mapping[str, object]:
    """Generate **only** the action config for clipboard use (without the find prefix).

    Used by *single --clip* mode where find + click are separated by ``---``.

    Args:
        selector: The best-effort selector (used by ``Find`` tool type only).
        tool: The target tool type.
        params: Generation parameters.

    Returns:
        A configuration dictionary for the action step only.
    """
    match tool:
        case ToolType.FIND:
            return build_find_config(selector, params.output_key)
        case ToolType.CLICK:
            return build_click_config(params.output_key)
        case ToolType.INPUT_TEXT | ToolType.SET_TEXT:
            return build_text_config(params.text, params.output_key)
        case ToolType.WAIT:
            return build_wait_config(params.duration_ms)


# ---------------------------------------------------------------------------
# Internal config builders
# ---------------------------------------------------------------------------


def build_find_config(selector: BestSelector, output_key: str) -> dict[str, object]:  # noqa: E501
    """Build a ``windows.find`` config from a captured selector.

    Selector priority:
        1. ``automation_id`` — most stable, use as the primary field.
        2. ``name`` + ``control_type`` — when ``automation_id`` is absent.
        3. ``class_name`` + ``control_type`` — fallback.

    ``control_type`` is included when available **and** not ``Custom``.

    Args:
        selector: The best-effort selector for a UI element.
        output_key: Key under which the found element will be stored.

    Returns:
        A configuration dictionary suitable for ``windows.find``.
    """
    config: dict[str, object] = {"output_key": output_key}

    if selector.automation_id:
        config["automation_id"] = selector.automation_id

    if selector.name:
        config["name"] = selector.name

    if selector.control_type and selector.control_type != "Custom":
        config["control_type"] = selector.control_type

    if selector.class_name:
        config["class_name"] = selector.class_name

    return config


def build_click_config(element_key: str) -> dict[str, str]:
    """Build a ``windows.click`` config referencing a previously found element.

    Args:
        element_key: The context key storing the target element.

    Returns:
        A configuration dictionary for ``windows.click``.
    """
    return {"element_key": element_key}


def build_text_config(text: str, element_key: str) -> dict[str, str]:
    """Build a config for ``windows.input_text`` or ``windows.set_text``.

    Both tools support ``element_key`` to reference a previously found element,
    as well as inline selector fields.

    Args:
        text: The text to type or set.
        element_key: The context key storing the target element.

    Returns:
        A configuration dictionary for a text-action tool.
    """
    return {"text": text, "element_key": element_key}


def build_wait_config(duration_ms: int) -> dict[str, int]:
    """Build a ``windows.wait`` config.

    Args:
        duration_ms: How long to wait in milliseconds.

    Returns:
        A configuration dictionary for ``windows.wait``.
    """
    return {"duration_ms": duration_ms}
