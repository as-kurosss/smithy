"""Engine tools — default tool registry with built-in tools."""

from __future__ import annotations

import sys

from smithy.core.registry import ToolRegistry
from smithy.engine.tools.http import HttpTool


def default_registry() -> ToolRegistry:
    """Create a registry pre-loaded with engine tools."""
    reg = ToolRegistry()
    reg.register(HttpTool())

    # Register Windows tools on Windows
    if sys.platform == "win32":
        from smithy.windows.tools.click import ClickTool
        from smithy.windows.tools.find import FindTool
        from smithy.windows.tools.process import ProcessTool

        reg.register(ProcessTool())
        reg.register(ClickTool())
        reg.register(FindTool())

    return reg
