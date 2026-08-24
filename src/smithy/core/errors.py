"""Error types for tool execution and the agent framework."""

from __future__ import annotations

from typing import Any


class ToolError(Exception):
    """Structured error for tool execution.

    Subclasses:
        InvalidInput — invalid or missing input parameters.
        ElementNotFound — UI element not found or inaccessible.
        Cancelled — operation cancelled by user or authority.
        PlatformError — platform or UIA error with underlying cause.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidInput(ToolError):
    """Invalid or missing input parameters."""

    def __init__(
        self,
        message: str,
        *,
        param: str | None = None,
        input_value: Any = None,
    ) -> None:
        super().__init__(message)
        self.param = param
        self.input_value = input_value


class ElementNotFound(ToolError):
    """UI element not found or inaccessible."""

    def __init__(
        self,
        message: str = "Element not found",
        *,
        selector: Any = None,
    ) -> None:
        super().__init__(message)
        self.selector = selector


class Cancelled(ToolError):
    """Operation cancelled by user or authority."""

    def __init__(self) -> None:
        super().__init__("Operation cancelled")


class PlatformError(ToolError):
    """Platform or UIA error with underlying cause."""

    def __init__(
        self,
        message: str,
        *,
        source: BaseException | None = None,
        input_value: Any = None,
    ) -> None:
        super().__init__(message)
        self.source = source
        self.input_value = input_value


class SmithError(Exception):
    """General-purpose error for the Smith framework.

    Bridges typed tool errors with the orchestrator layer.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidParams(SmithError):
    """Invalid parameters."""


class ContextError(SmithError):
    """Context-related error."""
