# Changelog

## 0.2.0

First minor release: transactions, config, and hardening on top of the
0.1.x tool core.

### Added

- Transactional queue model (`core/queue.py`): `Queue` protocol,
  `InMemoryQueue` / `SqliteQueue` with atomic FIFO claim, lease expiry,
  `max_attempts` requeue, idempotent add, `run_id` ownership; `HttpQueue`
  client for the orchestrator (stdlib only, retries on 502–504).
- REFramework-style runner (`core/transactions.py`): `run_transactions` /
  `run_transactions_async`, `BusinessError` vs `InfrastructureError`
  contract, `Cancelled` cooperative stop, background lease heartbeat
  (capped at 30 min), `on_progress` hook, `TransactionReport`.
- TOML robot config (`core/config.py`): `load_config` with fail-fast
  validation (`required` / `must_exist`), frozen attribute-style `Config`,
  `SMITHY_*` env overlay (`__` nests, TOML-typed values).
- Schema validation (`core/schema.py`): `ToolRegistry.execute` validates
  configs against `schema()` (hand-rolled subset, no new deps).
- Tool-level retries (`core/retry.py`): `RetryTool` wrapper
  (`attempts` / `delay_ms` / `retry_on`, defaults to `ElementNotFound`).
- JSONL audit log (`core/logging.py`): `JsonlEventLogger` middleware with
  `transaction_id`, duration, and error stamped per event.
- `windows_tools()` factory (`windows/tools/__init__.py`): default tool
  set in one call, UIA imports stay lazy.
- `ProcessTool` allowlist is now configurable: constructor param,
  `SMITHY_ALLOWED_COMMANDS` env override, `allowed_commands` introspection.
- `parse_control_type()` is public (`windows/selector.py`).
- Examples: `reframework_bot.py` (dispatcher + performer skeleton),
  `config_demo.py` with good/broken TOMLs.

### Changed

- Error model consolidated to the single `ToolError` family; the unused
  legacy `SmithError` / `InvalidParams` / `ContextError` were removed.

## 0.1.1

- Windows UI tools (process, click, wait, delay, screenshot, input_text,
  keyboard, set_text, get_element), selector capture CLI, middleware
  event bus, `@tool` decorator, `Smithy` facade.
