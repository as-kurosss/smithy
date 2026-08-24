"""Tests for smithy.engine.interpolate — {{var}} substitution."""

from __future__ import annotations

from smithy.core.context import ExecutionContext
from smithy.engine.interpolate import interpolate, interpolate_value


class TestInterpolate:
    def test_no_placeholders(self) -> None:
        ctx = ExecutionContext.create()
        assert interpolate("hello world", ctx) == "hello world"

    def test_single_placeholder(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("name", "Alice")
        assert interpolate("Hello {{name}}!", ctx) == "Hello Alice!"

    def test_multiple_placeholders(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("a", "foo")
        ctx.set("b", "bar")
        assert interpolate("{{a}}-{{b}}", ctx) == "foo-bar"

    def test_same_placeholder_twice(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("x", "Y")
        assert interpolate("{{x}} and {{x}}", ctx) == "Y and Y"

    def test_empty_string(self) -> None:
        ctx = ExecutionContext.create()
        assert interpolate("", ctx) == ""

    def test_placeholder_at_boundaries(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("v", "X")
        assert interpolate("{{v}}", ctx) == "X"
        assert interpolate("a{{v}}b", ctx) == "aXb"

    def test_missing_variable_keeps_placeholder(self) -> None:
        ctx = ExecutionContext.create()
        assert interpolate("{{missing}}", ctx) == "{{missing}}"

    def test_value_from_inner_scope(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("outer", "O")
        ctx.push_scope()
        ctx.set("inner", "I")
        assert interpolate("{{outer}}-{{inner}}", ctx) == "O-I"

    def test_inner_shadows_outer(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("x", "outer")
        ctx.push_scope()
        ctx.set("x", "inner")
        assert interpolate("{{x}}", ctx) == "inner"

    def test_numeric_value_coerced(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("count", 42)
        assert interpolate("Count: {{count}}", ctx) == "Count: 42"

    def test_bool_value_coerced(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("flag", True)
        assert interpolate("Flag: {{flag}}", ctx) == "Flag: True"

    def test_none_value_coerced(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("nothing", None)
        assert interpolate("Value: {{nothing}}", ctx) == "Value: None"

    def test_complex_dict_value_stringified(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("data", {"key": "val"})
        result = interpolate("{{data}}", ctx)
        assert isinstance(result, str)


class TestInterpolateValue:
    def test_string_value(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("x", "hello")
        assert interpolate_value("{{x}}", ctx) == "hello"

    def test_dict_value_string_interpolation(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("x", "world")
        result = interpolate_value("Hello {{x}}!", ctx)
        assert result == "Hello world!"

    def test_dict_pass_through(self) -> None:
        ctx = ExecutionContext.create()
        d = {"key": "val"}
        assert interpolate_value(d, ctx) == d

    def test_list_with_interpolation(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("a", "1")
        ctx.set("b", "2")
        result = interpolate_value(["{{a}}", "{{b}}"], ctx)
        assert result == ["1", "2"]

    def test_int_passthrough(self) -> None:
        ctx = ExecutionContext.create()
        assert interpolate_value(42, ctx) == 42

    def test_bool_passthrough(self) -> None:
        ctx = ExecutionContext.create()
        assert interpolate_value(True, ctx) is True

    def test_none_passthrough(self) -> None:
        ctx = ExecutionContext.create()
        assert interpolate_value(None, ctx) is None

    def test_nested_dict_interpolation(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("url", "http://example.com")
        d = {"endpoint": "{{url}}", "timeout": 30}
        result = interpolate_value(d, ctx)
        assert result == {"endpoint": "http://example.com", "timeout": 30}

    def test_nested_list_in_dict(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("item", "x")
        d = {"items": ["{{item}}", "y"]}
        result = interpolate_value(d, ctx)
        assert result == {"items": ["x", "y"]}
