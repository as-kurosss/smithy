"""Pytest configuration and fixtures."""

import pytest

from smithy.core.context import ExecutionContext
from smithy.core.registry import ToolRegistry


@pytest.fixture
def ctx() -> ExecutionContext:
    """Fresh execution context."""
    return ExecutionContext.create()


@pytest.fixture
def registry() -> ToolRegistry:
    """Fresh tool registry."""
    return ToolRegistry()
