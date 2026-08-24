"""Execution context with scoped variable storage."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContextValue:
    """Typed value stored in the execution context."""

    type_name: str
    value: Any

    @classmethod
    def from_any(cls, value: Any) -> ContextValue:
        """Create a ContextValue from a Python value."""
        if isinstance(value, str):
            return cls(type_name="String", value=value)
        if isinstance(value, bool):
            return cls(type_name="Boolean", value=value)
        if isinstance(value, (int, float)):
            return cls(type_name="Number", value=value)
        if isinstance(value, list):
            return cls(type_name="List", value=value)
        if value is None:
            return cls(type_name="Null", value=None)
        return cls(type_name="Object", value=value)

    def as_string(self) -> str:
        """Extract string value."""
        if self.type_name != "String":
            raise ValueError(f"Expected String, got {self.type_name}")
        return str(self.value)

    def as_number(self) -> float:
        """Extract numeric value."""
        if self.type_name != "Number":
            raise ValueError(f"Expected Number, got {self.type_name}")
        return float(self.value)

    def as_boolean(self) -> bool:
        """Extract boolean value."""
        if self.type_name != "Boolean":
            raise ValueError(f"Expected Boolean, got {self.type_name}")
        return bool(self.value)

    def display(self) -> str:
        """Human-readable display of the value."""
        if self.type_name == "String":
            return f'"{self.value}"'
        if self.type_name == "List":
            return f"[{len(self.value)} items]"
        if self.type_name == "Null":
            return "null"
        return str(self.value)


@dataclass
class ContextSnapshot:
    """Snapshot of a single context variable."""

    type_name: str
    value: str


# Type alias: variable name -> snapshot
ContextMap = dict[str, ContextSnapshot]


@dataclass
class ExecutionContext:
    """Scoped variable storage for tool execution.

    Uses a stack of scopes. Variables are looked up from
    the innermost scope outward.
    """

    _scopes: list[dict[str, ContextValue]] = field(default_factory=list)

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
        self._scopes[-1][key] = ContextValue.from_any(value)

    def get(self, key: str) -> ContextValue | None:
        """Look up a variable from innermost to outermost scope."""
        for scope in reversed(self._scopes):
            if key in scope:
                return scope[key]
        return None

    def snapshot(self) -> ContextMap:
        """Take a snapshot of all variables across all scopes."""
        result: ContextMap = {}
        for scope in self._scopes:
            for key, value in scope.items():
                result[key] = ContextSnapshot(
                    type_name=value.type_name,
                    value=value.display(),
                )
        return result
