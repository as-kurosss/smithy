"""Tests for smithy.core.context."""

from smithy.core.context import ExecutionContext


class TestExecutionContext:
    def test_create(self) -> None:
        ctx = ExecutionContext.create()
        assert ctx.get("nonexistent") is None

    def test_set_get(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("x", "hello")
        assert ctx.get("x") == "hello"

    def test_set_get_any_type(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("count", 42)
        ctx.set("items", [1, 2, 3])
        assert ctx.get("count") == 42
        assert ctx.get("items") == [1, 2, 3]

    def test_scope_shadowing(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("x", "outer")
        ctx.push_scope()
        ctx.set("x", "inner")
        assert ctx.get("x") == "inner"
        ctx.pop_scope()
        assert ctx.get("x") == "outer"

    def test_pop_scope_keeps_root(self) -> None:
        ctx = ExecutionContext.create()
        # Pop on single scope should be a no-op
        ctx.pop_scope()
        ctx.set("x", "val")
        assert ctx.get("x") == "val"

    def test_snapshot(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("name", "Alice")
        ctx.set("count", 5)
        snap = ctx.snapshot()
        assert snap["name"] == "Alice"
        assert snap["count"] == 5

    def test_snapshot_cross_scope(self) -> None:
        ctx = ExecutionContext.create()
        ctx.set("a", 1)
        ctx.push_scope()
        ctx.set("b", 2)
        snap = ctx.snapshot()
        assert snap["a"] == 1
        assert snap["b"] == 2