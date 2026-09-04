"""Tests for the transaction runner and its report."""

from __future__ import annotations

from typing import Any

import pytest

from smithy.core.errors import BusinessError, Cancelled, InfrastructureError, InvalidInput
from smithy.core.events import ToolEvent
from smithy.core.queue import ClaimedItem, InMemoryQueue, Queue
from smithy.core.transactions import (
    TransactionContextMiddleware,
    TransactionReport,
    current_transaction_id,
    run_transactions,
)

RUN_ID = "run-1"


def _seeded(count: int, max_attempts: int = 1) -> InMemoryQueue:
    queue = InMemoryQueue()
    queue.get_or_create_queue("jobs", max_attempts=max_attempts)
    for index in range(count):
        queue.add("jobs", {"n": index})
    return queue


def test_happy_path_processes_all_and_reports() -> None:
    queue = _seeded(2)
    seen: list[str] = []
    reports: list[TransactionReport] = []

    def process(item: ClaimedItem) -> dict[str, Any] | None:
        seen.append(item.id)
        assert current_transaction_id.get() == item.id
        return {"n": item.payload["n"]}

    report = run_transactions(
        queue,
        process,
        queue_name="jobs",
        run_id=RUN_ID,
        on_end=reports.append,
    )
    assert (report.succeeded, report.processed) == (2, 2)
    assert report.stop_reason == "queue_empty"
    assert [o.status for o in report.outcomes] == ["success", "success"]
    assert len(seen) == 2 and len(reports) == 1 and reports[0] is report


def test_on_init_seeds_before_first_claim() -> None:
    queue = InMemoryQueue()
    calls: list[str] = []

    def init(backend: Queue) -> None:
        calls.append("init")
        backend.get_or_create_queue("jobs")
        backend.add("jobs", {"n": 0})

    report = run_transactions(
        queue, lambda item: None, queue_name="jobs", run_id=RUN_ID, on_init=init
    )
    assert calls == ["init"] and report.succeeded == 1


def test_business_and_system_errors_split() -> None:
    queue = _seeded(3)

    def process(item: ClaimedItem) -> dict[str, Any] | None:
        if item.payload["n"] == 1:
            raise BusinessError("bad row")
        if item.payload["n"] == 2:
            raise RuntimeError("host exploded")
        return None

    report = run_transactions(queue, process, queue_name="jobs", run_id=RUN_ID)
    assert (report.succeeded, report.business_failed, report.system_failed) == (1, 1, 1)
    assert any("bad row" in error for error in report.errors)
    assert any("RuntimeError: host exploded" in error for error in report.errors)


def test_system_error_retries_until_budget() -> None:
    queue = _seeded(1, max_attempts=2)
    attempts: list[int] = []

    def process(item: ClaimedItem) -> dict[str, Any] | None:
        attempts.append(item.attempts)
        raise InfrastructureError("flaky host")

    report = run_transactions(queue, process, queue_name="jobs", run_id=RUN_ID)
    assert attempts == [1, 2]
    assert report.system_failed == 2
    assert report.stop_reason == "queue_empty"


def test_consecutive_system_budget_stops_loop() -> None:
    queue = _seeded(5, max_attempts=5)

    def process(item: ClaimedItem) -> dict[str, Any] | None:
        raise InfrastructureError("dead host")

    report = run_transactions(
        queue,
        process,
        queue_name="jobs",
        run_id=RUN_ID,
        stop_after_consecutive_system_errors=2,
    )
    assert report.stop_reason == "consecutive_system_errors"
    assert report.system_failed == 2
    assert report.consecutive_system_errors == 2
    # Business outcomes reset the streak: never trips here.
    assert queue.claim("jobs", run_id=RUN_ID) is not None


def test_business_outcome_resets_consecutive_streak() -> None:
    queue = _seeded(4, max_attempts=1)

    def process(item: ClaimedItem) -> dict[str, Any] | None:
        if item.payload["n"] == 1:
            raise BusinessError("bad row")
        if item.payload["n"] in (0, 2, 3):
            raise InfrastructureError("flaky")
        return None  # pragma: no cover

    report = run_transactions(
        queue,
        process,
        queue_name="jobs",
        run_id=RUN_ID,
        stop_after_consecutive_system_errors=3,
    )
    assert report.stop_reason == "queue_empty"
    assert (report.business_failed, report.system_failed) == (1, 3)


def test_stop_checker_ends_loop_cooperatively() -> None:
    queue = _seeded(3)
    polls = 0

    def checker() -> bool:
        nonlocal polls
        polls += 1
        return polls > 1

    report = run_transactions(
        queue, lambda item: None, queue_name="jobs", run_id=RUN_ID, stop_checker=checker
    )
    assert report.stop_reason == "stop_requested"
    assert report.succeeded == 1


def test_cancelled_releases_item_and_stops() -> None:
    queue = _seeded(2, max_attempts=2)

    def process(item: ClaimedItem) -> dict[str, Any] | None:
        if item.payload["n"] == 1:
            raise Cancelled()
        return None

    report = run_transactions(queue, process, queue_name="jobs", run_id=RUN_ID)
    assert report.stop_reason == "stop_requested"
    assert report.succeeded == 1
    recovered = queue.claim("jobs", run_id="run-2")
    assert recovered is not None and recovered.payload == {"n": 1}


def test_non_dict_result_becomes_system_failure() -> None:
    queue = _seeded(1)

    def process(item: ClaimedItem) -> Any:
        return "not-a-dict"

    report = run_transactions(queue, process, queue_name="jobs", run_id=RUN_ID)
    assert report.system_failed == 1
    assert "InvalidInput" in report.errors[0]


@pytest.mark.parametrize("bad", [0, -1, True, "10"])
def test_invalid_budget_rejected(bad: Any) -> None:
    queue = _seeded(1)
    with pytest.raises(InvalidInput):
        run_transactions(
            queue,
            lambda item: None,
            queue_name="jobs",
            run_id=RUN_ID,
            stop_after_consecutive_system_errors=bad,
        )


async def test_middleware_stamps_transaction_id() -> None:
    middleware = TransactionContextMiddleware()
    event = ToolEvent(tool_name="t", config={})
    assert (await middleware(event)) is event
    assert "transaction_id" not in event.metadata

    token = current_transaction_id.set("tx-1")
    try:
        await middleware(event)
    finally:
        current_transaction_id.reset(token)
    assert event.metadata["transaction_id"] == "tx-1"
