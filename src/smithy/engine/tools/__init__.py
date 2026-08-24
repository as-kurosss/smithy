"""Engine tools — default tool registry with built-in tools."""

from smithy.core.registry import ToolRegistry
from smithy.engine.tools.http import HttpTool


def default_registry() -> ToolRegistry:
    """Create a registry pre-loaded with engine tools."""
    reg = ToolRegistry()
    reg.register(HttpTool())
    return reg
