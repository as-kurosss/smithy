"""Smithy — Free Python RPA engine for creating automation bots."""

from smithy.core.errors import (
    BusinessError,
    Cancelled,
    ElementNotFound,
    InfrastructureError,
    InvalidInput,
    PlatformError,
    ToolError,
)
from smithy.core.http_queue import HttpQueue, HttpQueueError
from smithy.core.queue import (
    ClaimedItem,
    InMemoryQueue,
    Queue,
    QueueInfo,
    QueueItem,
    SqliteQueue,
)
from smithy.core.tool import AbstractTool, Tool, tool
from smithy.core.transactions import (
    ItemOutcome,
    TransactionContextMiddleware,
    TransactionReport,
    current_transaction_id,
    run_transactions,
)
from smithy.facade import ClickResult, ProcessHandle, Smithy

__version__ = "0.1.1"

__all__ = [
    "AbstractTool",
    "BusinessError",
    "Cancelled",
    "ClaimedItem",
    "ClickResult",
    "ElementNotFound",
    "HttpQueue",
    "HttpQueueError",
    "InMemoryQueue",
    "InvalidInput",
    "ItemOutcome",
    "PlatformError",
    "ProcessHandle",
    "Queue",
    "QueueInfo",
    "QueueItem",
    "Smithy",
    "SqliteQueue",
    "InfrastructureError",
    "Tool",
    "ToolError",
    "TransactionContextMiddleware",
    "TransactionReport",
    "current_transaction_id",
    "run_transactions",
    "tool",
]
