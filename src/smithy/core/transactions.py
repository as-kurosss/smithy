"""Transactional runner in the UiPath REFramework spirit.

The loop is framework-owned and queue-agnostic: ``Init`` (seed via
``on_init``) → ``Get`` (:meth:`Queue.claim`) → ``Process``
(``process_fn``) → ``SetStatus`` (:meth:`Queue.set_status`) → ``End``
(report via ``on_end``).

Error contract for ``process_fn``:

- :class:`BusinessError` — bad data, terminal ``business_failed``.
- :class:`InfrastructureError` (or any unexpected exception) — infra failure,
  ``system_failed`` (requeued within the queue budget).
- :class:`Cancelled` — cooperative stop: the item is released back as
  ``system_failed`` and the loop ends with ``stop_requested``.

Long items: when the queue supports :class:`LeaseRenewable`, the runner
renews the claim lease in the background (heartbeat) so a slow
``process_fn`` doesn't lose its item. Renewal stops after
``max_claim_seconds`` (default 30 minutes) — past that the lease expires
and the item becomes claimable by another run. If our run then records
the outcome, the backend answers ``InvalidInput`` (HTTP 409) and the
runner logs an ``OwnershipLost`` outcome instead of crashing.
"""

from __future__ import annotations

import asyncio
import inspect
import threading
import time
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Literal

from smithy.core.errors import BusinessError, Cancelled, InfrastructureError, InvalidInput
from smithy.core.events import ToolEvent
from smithy.core.queue import ClaimedItem, FinalStatus, LeaseRenewable, Queue

#: Id of the transaction currently processed in this context (if any).
#: Stamped onto every :class:`ToolEvent` by :class:`TransactionContextMiddleware`.
current_transaction_id: ContextVar[str | None] = ContextVar("smithy_transaction_id", default=None)

StopReason = Literal["queue_empty", "stop_requested", "consecutive_system_errors"]


class TransactionContextMiddleware:
    """Stamp ``transaction_id`` into ``ToolEvent.metadata`` when in a transaction."""

    async def __call__(self, event: ToolEvent) -> ToolEvent | None:
        transaction_id = current_transaction_id.get()
        if transaction_id is not None:
            event.metadata["transaction_id"] = transaction_id
        return event


@dataclass
class ItemOutcome:
    """Final outcome of one processed transaction."""

    item_id: str
    status: FinalStatus
    attempts: int
    error: str | None = None


@dataclass
class TransactionReport:
    """Business-readable summary of a runner session (the ``End`` step)."""

    queue_name: str
    run_id: str
    succeeded: int = 0
    business_failed: int = 0
    system_failed: int = 0
    consecutive_system_errors: int = 0
    stop_reason: StopReason = "queue_empty"
    outcomes: list[ItemOutcome] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    heartbeat_active: bool = False
    """Whether a lease-renewal heartbeat ran for at least one item."""
    lease_renewals: int = 0
    """Total successful lease renewals this session."""

    @property
    def processed(self) -> int:
        """Total items that reached a terminal state this session."""
        return self.succeeded + self.business_failed + self.system_failed


def _check_positive_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise InvalidInput(f"{name} must be an int >= 1", param=name, input_value=value)


def _renew_interval(lease_seconds: int) -> float:
    """Seconds between renewals: a third of the lease, clamped to 1–30 s."""
    return max(1.0, min(lease_seconds / 3.0, 30.0))


def _try_set_status(
    queue: Queue,
    item_id: str,
    status: FinalStatus,
    *,
    run_id: str,
    error: str | None = None,
    result: dict[str, Any] | None = None,
) -> str | None:
    """Record the outcome; return ``None`` or an ``OwnershipLost`` message.

    ``InvalidInput`` means the claim moved on (lease expired, another run
    claimed it) — the caller's counters treat it as a system failure.
    """
    try:
        queue.set_status(item_id, status, run_id=run_id, error=error, result=result)
    except InvalidInput as exc:
        return f"OwnershipLost: {exc}"
    return None


def _lost_outcome(report: TransactionReport, item: ClaimedItem, message: str) -> ItemOutcome:
    """Append a system-failure outcome the backend refused to record."""
    report.system_failed += 1
    outcome = ItemOutcome(item.id, "system_failed", item.attempts, message)
    report.errors.append(f"{item.id}: {message}")
    return outcome


def _emit_progress(hook: Callable[[ItemOutcome], None] | None, outcome: ItemOutcome) -> None:
    if hook is not None:
        hook(outcome)


async def _maybe_await(value: Any) -> Any:
    """Await *value* when awaitable, else return it as-is."""
    if inspect.isawaitable(value):
        return await value
    return value


async def _emit_progress_async(
    hook: Callable[[ItemOutcome], Any] | None, outcome: ItemOutcome
) -> None:
    if hook is not None:
        await _maybe_await(hook(outcome))


class _SyncHeartbeat:
    """Background thread renewing one claim until stopped or the cap hits."""

    def __init__(
        self,
        queue: LeaseRenewable,
        item: ClaimedItem,
        *,
        run_id: str,
        lease_seconds: int,
        max_claim_seconds: int,
    ) -> None:
        self._queue = queue
        self._item = item
        self._run_id = run_id
        self._lease_seconds = lease_seconds
        self._max_claim_seconds = max_claim_seconds
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self.renewals = 0

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        """Signal the thread and wait for it (bounds the renewal count)."""
        self._stop.set()
        self._thread.join()

    def _run(self) -> None:
        interval = _renew_interval(self._lease_seconds)
        start = time.monotonic()
        while not self._stop.wait(interval):
            if time.monotonic() - start >= self._max_claim_seconds:
                return
            try:
                self._queue.renew_lease(
                    self._item.id, run_id=self._run_id, lease_seconds=self._lease_seconds
                )
            except (InvalidInput, KeyError):
                return  # Claim moved on or vanished; the outcome write reports it.
            except Exception:
                continue  # Transient transport blip; retry on the next interval.
            self.renewals += 1


async def _async_heartbeat(
    queue: LeaseRenewable,
    item: ClaimedItem,
    *,
    run_id: str,
    lease_seconds: int,
    max_claim_seconds: int,
    stop: asyncio.Event,
    report: TransactionReport,
) -> None:
    """Renew one claim until *stop* is set or the total cap elapses."""
    interval = _renew_interval(lease_seconds)
    start = time.monotonic()
    while True:
        try:
            async with asyncio.timeout(interval):
                await stop.wait()
            return
        except TimeoutError:
            pass
        if time.monotonic() - start >= max_claim_seconds:
            return
        try:
            await asyncio.to_thread(
                queue.renew_lease, item.id, run_id=run_id, lease_seconds=lease_seconds
            )
        except (InvalidInput, KeyError):
            return  # Claim moved on or vanished; the outcome write reports it.
        except Exception:
            continue  # Transient transport blip; retry on the next interval.
        report.lease_renewals += 1


def run_transactions(
    queue: Queue,
    process_fn: Callable[[ClaimedItem], dict[str, Any] | None],
    *,
    queue_name: str,
    run_id: str,
    lease_seconds: int = 300,
    stop_after_consecutive_system_errors: int = 10,
    stop_checker: Callable[[], bool] | None = None,
    on_init: Callable[[Queue], None] | None = None,
    on_end: Callable[[TransactionReport], None] | None = None,
    on_progress: Callable[[ItemOutcome], None] | None = None,
    heartbeat: bool = True,
    max_claim_seconds: int = 1800,
) -> TransactionReport:
    """Run the transaction loop until the queue drains or a stop triggers.

    Parameters
    ----------
    queue: Backend implementing the :class:`Queue` protocol.
    process_fn: Business logic for one item; returns an optional result
        dict stored with the ``success`` status.
    queue_name: Queue to consume.
    run_id: Stable id of this run (recorded on every claim).
    lease_seconds: Claim lease handed to the queue backend.
    stop_after_consecutive_system_errors: Abort the loop after this many
        systemic failures in a row (a dead host, not bad data).
    stop_checker: Polled before every claim; ``True`` ends the loop with
        ``stop_requested`` (wire to the orchestrator run status).
    on_init: Dispatcher hook — seed the queue before the first claim.
    on_end: Reporting hook — receives the finished report.
    on_progress: Per-item hook — called with each :class:`ItemOutcome`
        right after it is recorded (log it, move a progress bar).
    heartbeat: Renew the claim lease in the background while ``process_fn``
        runs (only when the queue supports :class:`LeaseRenewable`).
    max_claim_seconds: Stop renewing after this many seconds per claim
        (default 1800 — 30 minutes); past that the lease may expire and
        another run can pick the item up.
    """
    _check_positive_int(
        "stop_after_consecutive_system_errors", stop_after_consecutive_system_errors
    )
    _check_positive_int("max_claim_seconds", max_claim_seconds)

    if on_init is not None:
        on_init(queue)

    report = TransactionReport(queue_name=queue_name, run_id=run_id)
    consecutive = 0

    while True:
        if stop_checker is not None and stop_checker():
            report.stop_reason = "stop_requested"
            break
        item = queue.claim(queue_name, run_id=run_id, lease_seconds=lease_seconds)
        if item is None:
            report.stop_reason = "queue_empty"
            break

        token = current_transaction_id.set(item.id)
        beat: _SyncHeartbeat | None = None
        try:
            if heartbeat and isinstance(queue, LeaseRenewable):
                beat = _SyncHeartbeat(
                    queue,
                    item,
                    run_id=run_id,
                    lease_seconds=lease_seconds,
                    max_claim_seconds=max_claim_seconds,
                )
                beat.start()
                report.heartbeat_active = True
            result = process_fn(item)
            if result is not None and not isinstance(result, dict):
                raise InvalidInput(
                    f"process_fn must return a dict or None, got {type(result).__name__}",
                    param="result",
                )
            lost = _try_set_status(queue, item.id, "success", run_id=run_id, result=result)
            if lost is None:
                report.succeeded += 1
                consecutive = 0
                outcome = ItemOutcome(item.id, "success", item.attempts)
            else:
                consecutive += 1
                outcome = _lost_outcome(report, item, lost)
        except BusinessError as exc:
            lost = _try_set_status(queue, item.id, "business_failed", run_id=run_id, error=str(exc))
            if lost is None:
                report.business_failed += 1
                consecutive = 0
                outcome = ItemOutcome(item.id, "business_failed", item.attempts, str(exc))
                report.errors.append(f"{item.id}: {exc}")
            else:
                consecutive += 1
                outcome = _lost_outcome(report, item, lost)
        except Cancelled as exc:
            lost = _try_set_status(
                queue, item.id, "system_failed", run_id=run_id, error=f"Cancelled: {exc}"
            )
            if lost is None:
                report.system_failed += 1
                outcome = ItemOutcome(item.id, "system_failed", item.attempts, f"Cancelled: {exc}")
            else:
                outcome = _lost_outcome(report, item, lost)
            report.stop_reason = "stop_requested"
            report.outcomes.append(outcome)
            _emit_progress(on_progress, outcome)
            break
        except (InfrastructureError, Exception) as exc:
            lost = _try_set_status(
                queue,
                item.id,
                "system_failed",
                run_id=run_id,
                error=f"{type(exc).__name__}: {exc}",
            )
            if lost is None:
                report.system_failed += 1
                consecutive += 1
                outcome = ItemOutcome(
                    item.id, "system_failed", item.attempts, f"{type(exc).__name__}: {exc}"
                )
                report.errors.append(f"{item.id}: {type(exc).__name__}: {exc}")
            else:
                consecutive += 1
                outcome = _lost_outcome(report, item, lost)
            if consecutive >= stop_after_consecutive_system_errors:
                report.stop_reason = "consecutive_system_errors"
                report.outcomes.append(outcome)
                _emit_progress(on_progress, outcome)
                break
        finally:
            if beat is not None:
                beat.stop()
                report.lease_renewals += beat.renewals
            current_transaction_id.reset(token)
        report.outcomes.append(outcome)
        _emit_progress(on_progress, outcome)

    report.consecutive_system_errors = consecutive
    if on_end is not None:
        on_end(report)
    return report


async def run_transactions_async(
    queue: Queue,
    process_fn: Callable[[ClaimedItem], Awaitable[dict[str, Any] | None] | dict[str, Any] | None],
    *,
    queue_name: str,
    run_id: str,
    lease_seconds: int = 300,
    stop_after_consecutive_system_errors: int = 10,
    stop_checker: Callable[[], bool | Awaitable[bool]] | None = None,
    on_init: Callable[[Queue], Any] | None = None,
    on_end: Callable[[TransactionReport], Any] | None = None,
    on_progress: Callable[[ItemOutcome], Any] | None = None,
    heartbeat: bool = True,
    max_claim_seconds: int = 1800,
) -> TransactionReport:
    """Async twin of :func:`run_transactions` for ``async def`` business logic.

    Same loop, same report, same error contract — but ``process_fn`` and
    every hook may be ``async def`` (plain sync callables work too).
    Queue calls run in a worker thread so the event loop never blocks.
    """
    _check_positive_int(
        "stop_after_consecutive_system_errors", stop_after_consecutive_system_errors
    )
    _check_positive_int("max_claim_seconds", max_claim_seconds)

    if on_init is not None:
        await _maybe_await(on_init(queue))

    report = TransactionReport(queue_name=queue_name, run_id=run_id)
    consecutive = 0

    while True:
        if stop_checker is not None and await _maybe_await(stop_checker()):
            report.stop_reason = "stop_requested"
            break
        item = await asyncio.to_thread(
            queue.claim, queue_name, run_id=run_id, lease_seconds=lease_seconds
        )
        if item is None:
            report.stop_reason = "queue_empty"
            break

        token = current_transaction_id.set(item.id)
        stop_beat = asyncio.Event()
        beat_task: asyncio.Task[None] | None = None
        try:
            if heartbeat and isinstance(queue, LeaseRenewable):
                beat_task = asyncio.create_task(
                    _async_heartbeat(
                        queue,
                        item,
                        run_id=run_id,
                        lease_seconds=lease_seconds,
                        max_claim_seconds=max_claim_seconds,
                        stop=stop_beat,
                        report=report,
                    )
                )
                report.heartbeat_active = True
            raw: Any = process_fn(item)
            if inspect.isawaitable(raw):
                raw = await raw
            result: dict[str, Any] | None = raw
            if result is not None and not isinstance(result, dict):
                raise InvalidInput(
                    f"process_fn must return a dict or None, got {type(result).__name__}",
                    param="result",
                )
            lost = await asyncio.to_thread(
                _try_set_status, queue, item.id, "success", run_id=run_id, result=result
            )
            if lost is None:
                report.succeeded += 1
                consecutive = 0
                outcome = ItemOutcome(item.id, "success", item.attempts)
            else:
                consecutive += 1
                outcome = _lost_outcome(report, item, lost)
        except BusinessError as exc:
            lost = await asyncio.to_thread(
                _try_set_status,
                queue,
                item.id,
                "business_failed",
                run_id=run_id,
                error=str(exc),
            )
            if lost is None:
                report.business_failed += 1
                consecutive = 0
                outcome = ItemOutcome(item.id, "business_failed", item.attempts, str(exc))
                report.errors.append(f"{item.id}: {exc}")
            else:
                consecutive += 1
                outcome = _lost_outcome(report, item, lost)
        except Cancelled as exc:
            lost = await asyncio.to_thread(
                _try_set_status,
                queue,
                item.id,
                "system_failed",
                run_id=run_id,
                error=f"Cancelled: {exc}",
            )
            if lost is None:
                report.system_failed += 1
                outcome = ItemOutcome(item.id, "system_failed", item.attempts, f"Cancelled: {exc}")
            else:
                outcome = _lost_outcome(report, item, lost)
            report.stop_reason = "stop_requested"
            report.outcomes.append(outcome)
            await _emit_progress_async(on_progress, outcome)
            break
        except (InfrastructureError, Exception) as exc:
            lost = await asyncio.to_thread(
                _try_set_status,
                queue,
                item.id,
                "system_failed",
                run_id=run_id,
                error=f"{type(exc).__name__}: {exc}",
            )
            if lost is None:
                report.system_failed += 1
                consecutive += 1
                outcome = ItemOutcome(
                    item.id, "system_failed", item.attempts, f"{type(exc).__name__}: {exc}"
                )
                report.errors.append(f"{item.id}: {type(exc).__name__}: {exc}")
            else:
                consecutive += 1
                outcome = _lost_outcome(report, item, lost)
            if consecutive >= stop_after_consecutive_system_errors:
                report.stop_reason = "consecutive_system_errors"
                report.outcomes.append(outcome)
                await _emit_progress_async(on_progress, outcome)
                break
        finally:
            if beat_task is not None:
                stop_beat.set()
                await beat_task
            current_transaction_id.reset(token)
        report.outcomes.append(outcome)
        await _emit_progress_async(on_progress, outcome)

    report.consecutive_system_errors = consecutive
    if on_end is not None:
        await _maybe_await(on_end(report))
    return report
