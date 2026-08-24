"""Tests for smithy.core.context."""

import pytest

from smithy.core.context import ContextSnapshot, ContextValue, ExecutionContext


class TestContextValue:
    def test_from_string(self) -> None:
        v = ContextValue.from_any("hello")
        assert v.type_name == "String"
        assert v.value == "hello"

    def test_from_bool(self) -> None:
        v = ContextValue.from_any(True)
        assert v.type_name == "Boolean"
        assert v.value is True

    def test_from_int(self) -> None:
        v = ContextValue.from_any(42)
        assert v.type_name == "Number"
        assert v.value == 42

    def test_from_float(self) -> None:
        v = ContextValue.from_any(3.14)
        assert v.type_name == "Number"
        assert v.value == 3.14

    def test_from_list(self) -> None:
        v = ContextValue.from_any([1, 2, 3])
        assert v.type_name == "List"
        assert v.value == [1, 2, 3]

    def test_from_none(self) -> None:
        v = ContextValue.from_any(None)
        assert v.type_name == "Null"
        assert v.value is None

    def test_from_dict(self) -> None:
        v = ContextValue.from_any({"key": "val"})
        assert v.type_name == "Object"

    def test_as_string_ok(self) -> None:
        v = ContextValue.from_any("hi")
        assert v.as_string() == "hi"

    def test_as_string_wrong_type(self) -> None:
        v = ContextValue.from_any(42)
        with pytest.raises(ValueError, match="Expected String"):
            v.as_string()

    def test_as_number_ok(self) -> None:
        v = ContextValue.from_any(7)
        assert v.as_number() == 7.0

    def test_as_number_wrong_type(self) -> None:
        v = ContextValue.from_any("text")
        with pytest.raises(ValueError, match="Expected Number"):
            v.as_number()

    def test_as_boolean_ok(self) -> None:
        v = ContextValue.from_any(False)
        assert v.as_boolean() is False

    def test_as_boolean_wrong_type(self) -> None:
        v = ContextValue.from_any(1)
        with pytest.raises(ValueError, match="Expected Boolean"):
            v.as_boolean()

    def test_display_string(self) -> None:
        v = ContextValue.from_any("hello")
        assert v.display() == '"hello"'

    def test_display_list(self) -> None:
        v = ContextValue.from_any([1, 2, 3])
        assert v.display() == "[3 items]"

    def test_display_null(self) -> None:
        v = ContextValue.from_any(None)
        assert v.display() == "null"

    def test_display_number(self) -> None:
        v = ContextValue.from_any(42)
        assert v.display() == "42"


class TestContextSnapshot:
    def test_fields(self) -> None:
        s = ContextSnapshot(type_name="String", value='"hi"')
        assert s.type_name == "String"
        assert s.value == '"hi"'


class TestExecutionContext:
    def test_create(self) -> None:
        ctx = ExecutionContext.create()
        assert ctx.get("nonexistent") is None

    def test_set_get(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("x", "hello")
        val = ctx.get("x")
        assert val is not None
        assert val.as_string() == "hello"

    def test_scope_shadowing(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("x", "outer")
        ctx.push_scope()
        ctx.set("x", "inner")
        val = ctx.get("x")
        assert val is not None
        assert val.as_string() == "inner"
        ctx.pop_scope()
        val = ctx.get("x")
        assert val is not None
        assert val.as_string() == "outer"

    def test_pop_scope_keeps_root(self) -> None:
        ctx = ExecutionContext.create()
        # Pop on single scope should be a no-op
        ctx.pop_scope()
        ctx.set("x", "val")
        assert ctx.get("x") is not None

    def test_snapshot(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("name", "Alice")
        ctx.set("count", 5)
        snap = ctx.snapshot()
        assert "name" in snap
        assert "count" in snap
        assert snap["name"].type_name == "String"
        assert snap["count"].type_name == "Number"

    def test_snapshot_cross_scope(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("a", 1)
        ctx.push_scope()
        ctx.set("b", 2)
        snap = ctx.snapshot()
        assert "a" in snap
        assert "b" in snap
