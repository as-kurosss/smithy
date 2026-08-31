"""Smithy — Free Python RPA engine for creating automation bots."""

from smithy.core.errors import (
    Cancelled,
    ElementNotFound,
    InvalidInput,
    PlatformError,
    ToolError,
)
from smithy.core.tool import AbstractTool, Tool, tool
from smithy.facade import ClickResult, ProcessHandle, Smithy

__version__ = "0.1.0"

__all__ = [
    "AbstractTool",
    "Cancelled",
    "ClickResult",
    "ElementNotFound",
    "InvalidInput",
    "PlatformError",
    "ProcessHandle",
    "Smithy",
    "Tool",
    "ToolError",
    "tool",
]
