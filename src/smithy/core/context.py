"""Execution context with scoped variable storage."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionContext:
    """Scoped variable storage for tool execution.

    Uses a stack of scopes.  Variables are looked up from
    the innermost scope outward.
    """
    _scopes: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self._scopes:
            self._scopes = [{}]

    @classmethod
    def create(cls) -> ExecutionContext:
        """Create a new empty context."""
        return cls()

    def push_scope(self) -> None:
        """Push a new local scope."""
        self._scopes.append({})

    def pop_scope(self) -> None:
        """Pop the current scope (keeps at least one)."""
        if len(self._scopes) > 1:
            self._scopes.pop()

    def set(self, key: str, value: Any) -> None:
        """Set a variable in the current (topmost) scope."""
        self._scopes[-1][key] = value

    def get(self, key: str) -> Any | None:
        """Look up a variable from innermost to outermost scope."""
        for scope in reversed(self._scopes):
            if key in scope:
                return scope[key]
        return None

    def snapshot(self) -> dict[str, Any]:
        """Take a snapshot of all variables across all scopes."""
        result: dict[str, Any] = {}
        for scope in self._scopes:
            result.update(scope)
        return result
