"""Pytest configuration and fixtures."""

import pytest

from smithy.core.registry import ToolRegistry


@pytest.fixture
def registry() -> ToolRegistry:
    """Fresh tool registry."""
    return ToolRegistry()
