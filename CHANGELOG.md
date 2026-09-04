# Changelog

## 0.3.0

GUI batch: comfortable desktop automation on top of the 0.2.0 core.

### Added

- Ten new Windows tools: `windows.scroll` (wheel over element/point),
  `windows.hover` (menus, tooltips), `windows.exists` (single-lookup
  boolean), `windows.get_text` (ValuePattern → Name fallback),
  `windows.window` (activate/minimize/maximize/restore/move/close by PID
  via Win32), `windows.select` (dropdown/combobox/list via
  SelectionItemPattern), `windows.drag` (two endpoints, coordinates or
  `from_*`/`to_*` selectors), `windows.clipboard` (get/set via
  `pyperclip`), `windows.list_elements` (direct-children dump for
  discovering automation IDs), `windows.highlight` (colored rectangle
  flash for debugging selectors).
- `Smithy` facade methods for every new tool (`scroll`, `hover`,
  `exists`, `get_text`, `window`, `select`, `drag`, `clipboard`,
  `list_elements`, `highlight`), all accepting an optional `handle` for
  PID scoping.
- Shared `_resolve.py` helpers: `resolve_point` (coordinates win over
  selectors) and `resolve_element`.

### Changed

- `windows.click` now takes `button` (left/right), `clicks` (1/2), and
  `x`/`y` coordinate clicks (double right-click = two `RightClick`
  calls; no module-level `DoubleClick` exists in `uiautomation`).
- `windows.wait` now takes `wait_for` (`appear`/`disappear`) with a
  symmetric poll loop; `PlatformError` mid-poll counts as still present.
- `smithy[windows]` extra now includes `pyperclip` (clipboard support).

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
