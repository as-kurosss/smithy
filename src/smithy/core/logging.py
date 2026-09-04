"""JSONL event sink — append-only audit log of tool executions.

Attach to a bot in one line::

    bot.add_middleware(JsonlEventLogger("bot-data/runs.jsonl"))

Every :class:`ToolEvent` becomes one JSON object per line: timestamp,
tool name, current ``transaction_id`` (when inside a transaction run),
duration, error (if any), plus the config and result. JSONL is
grep-able with plain tools and importable into log analysers —
the standard answer to "разбор полётов после ошибок".
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TextIO

from smithy.core.events import ToolEvent
from smithy.core.transactions import current_transaction_id


class JsonlEventLogger:
    """Middleware that appends each :class:`ToolEvent` as one JSON line.

    The file is opened in append mode at construction, so a bot with an
    unwritable audit log fails fast in Init instead of silently losing
    history. Call :meth:`close` (or use the logger for the whole bot
    lifetime) to flush and release the handle.

    Args:
        path: JSONL file to append to. Missing parent directories are
            *not* created — a bad path raises ``OSError`` immediately.
        include_config: Record the tool input (disable for sensitive data).
        include_result: Record the tool output.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        include_config: bool = True,
        include_result: bool = True,
    ) -> None:
        self._path = Path(path)
        self._include_config = include_config
        self._include_result = include_result
        self._file: TextIO = self._path.open("a", encoding="utf-8")

    async def __call__(self, event: ToolEvent) -> ToolEvent | None:
        """Append *event* to the log and pass it down the pipeline."""
        error = event.error
        record: dict[str, Any] = {
            "ts": event.timestamp.isoformat(),
            "tool": event.tool_name,
            "transaction_id": current_transaction_id.get(),
            "duration_ms": round(event.duration_ms, 3),
            "error": (
                None if error is None else {"type": type(error).__name__, "message": str(error)}
            ),
        }
        if self._include_config:
            record["config"] = event.config
        if self._include_result:
            record["result"] = event.result
        self._file.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        self._file.flush()
        return event

    def close(self) -> None:
        """Flush and close the underlying file."""
        self._file.close()
