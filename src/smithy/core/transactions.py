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
"""

from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Literal

from smithy.core.errors import BusinessError, Cancelled, InfrastructureError, InvalidInput
from smithy.core.events import ToolEvent
from smithy.core.queue import ClaimedItem, FinalStatus, Queue

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

    @property
    def processed(self) -> int:
        """Total items that reached a terminal state this session."""
        return self.succeeded + self.business_failed + self.system_failed


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
    """
    if isinstance(stop_after_consecutive_system_errors, bool) or not isinstance(
        stop_after_consecutive_system_errors, int
    ):
        raise InvalidInput(
            "stop_after_consecutive_system_errors must be an int",
            param="stop_after_consecutive_system_errors",
        )
    if stop_after_consecutive_system_errors < 1:
        raise InvalidInput(
            "stop_after_consecutive_system_errors must be >= 1",
            param="stop_after_consecutive_system_errors",
        )

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
        try:
            result = process_fn(item)
            if result is not None and not isinstance(result, dict):
                raise InvalidInput(
                    f"process_fn must return a dict or None, got {type(result).__name__}",
                    param="result",
                )
            queue.set_status(item.id, "success", run_id=run_id, result=result)
            report.succeeded += 1
            consecutive = 0
            report.outcomes.append(ItemOutcome(item.id, "success", item.attempts))
        except BusinessError as exc:
            queue.set_status(item.id, "business_failed", run_id=run_id, error=str(exc))
            report.business_failed += 1
            consecutive = 0
            report.outcomes.append(ItemOutcome(item.id, "business_failed", item.attempts, str(exc)))
            report.errors.append(f"{item.id}: {exc}")
        except Cancelled as exc:
            queue.set_status(item.id, "system_failed", run_id=run_id, error=f"Cancelled: {exc}")
            report.system_failed += 1
            report.outcomes.append(
                ItemOutcome(item.id, "system_failed", item.attempts, f"Cancelled: {exc}")
            )
            report.stop_reason = "stop_requested"
            break
        except (InfrastructureError, Exception) as exc:
            queue.set_status(
                item.id, "system_failed", run_id=run_id, error=f"{type(exc).__name__}: {exc}"
            )
            report.system_failed += 1
            consecutive += 1
            report.outcomes.append(
                ItemOutcome(item.id, "system_failed", item.attempts, f"{type(exc).__name__}: {exc}")
            )
            report.errors.append(f"{item.id}: {type(exc).__name__}: {exc}")
            if consecutive >= stop_after_consecutive_system_errors:
                report.stop_reason = "consecutive_system_errors"
                break
        finally:
            current_transaction_id.reset(token)

    report.consecutive_system_errors = consecutive
    if on_end is not None:
        on_end(report)
    return report
