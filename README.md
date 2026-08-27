# Smithy

Free Python RPA engine — create automation bots with simple API.

## Quick Start

```python
import asyncio
from smithy import Smithy
from smithy.windows.tools.click import ClickTool
from smithy.windows.tools.find import FindTool
from smithy.windows.tools.process import ProcessTool

bot = Smithy(tools=[ProcessTool(), FindTool(), ClickTool()])

async def main():
    # Launch app — returns ProcessHandle with PID
    app = await bot.process("notepad.exe")

    # Interact with UI — PID scopes element search
    await bot.click(app, name="File")
    await bot.click(app, name="Save As...")

asyncio.run(main())
```

## Custom Tools

```python
from smithy import Smithy, tool
from smithy.core.context import ExecutionContext

@tool("greet", description="Greet a person")
async def greet(config: dict, ctx: ExecutionContext) -> dict:
    name = config.get("name", "World")
    return {"message": f"Hello, {name}!"}

bot = Smithy(tools=[greet])

async def main():
    result = await bot.call("greet", name="Alice")
    print(result["message"])  # Hello, Alice!
```

## Install

```bash
pip install smithy

# Windows UIA tools
pip install smithy[windows]

# Selector capture (pynput + pyperclip)
pip install smithy[capture]

# All optional dependencies
pip install smithy[all]

# Development
pip install -e ".[dev]"
```

## Development

```bash
# Using uv (recommended)
uv venv .venv
.venv\Scripts\activate
uv pip install -e ".[dev,windows,capture]"

# Or with pip
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev,windows,capture]"

pytest                    # run tests (252+ tests)
ruff check src/ tests/    # linter
mypy src/smithy --strict  # type check
```

## Structure

```
src/smithy/
├── __init__.py   — Public API: Smithy, ProcessHandle, Tool, errors
├── facade.py     — Smithy facade class
├── core/         — Tool ABC, @tool decorator, ExecutionContext, ToolRegistry
├── engine/       — Robot/Step models, executor, HTTP tool (JSON robots)
├── windows/      — UIA tools (click, find, process)
├── orchestrator/ — Job manager, debug controller
├── server/       — FastAPI REST API
└── cli/          — CLI: validate / run
```

## Examples

- [`examples/basic_bot.py`](examples/basic_bot.py) — RPA bot with ProcessHandle API
- [`examples/custom_tool.py`](examples/custom_tool.py) — Custom tools with @tool decorator

## License

MIT
