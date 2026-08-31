# Smithy

Free Python RPA engine — create automation bots with simple async API.

## Quick Start

```python
import asyncio
from smithy import Smithy
from smithy.windows.tools.process import ProcessTool
from smithy.windows.tools.find import FindTool
from smithy.windows.tools.click import ClickTool
from smithy.windows.tools.wait import WaitTool
from smithy.windows.tools.delay import DelayTool
from smithy.windows.tools.screenshot import ScreenshotTool
from smithy.windows.tools.input_text import InputTextTool
from smithy.windows.tools.set_text import SetTextTool
from smithy.windows.tools.get_element import GetElementTool

bot = Smithy(
    tools=[
        ProcessTool(),
        FindTool(),
        ClickTool(),
        WaitTool(),
        DelayTool(),
        ScreenshotTool(),
        InputTextTool(),
        SetTextTool(),
        GetElementTool(),
    ]
)


async def main() -> None:
    app = await bot.process_run("notepad.exe")
    await bot.wait(app, class_name="Notepad", name="*Notepad")
    await bot.click(app, name="File")
    await bot.delay(duration_ms=300)
    await bot.click(app, name="Save As...")
    await bot.input_text(app, text="hello world")
    await bot.input_text(text="ctrl+s")
    await bot.screenshot("notepad.png")
    await bot.process_stop(app)


asyncio.run(main())
```

## Built-in Tools

- **ProcessTool** (`windows.process`) — launch and stop Windows processes by name
- **FindTool** (`windows.find`) — locate a UI element and store it in context
- **ClickTool** (`windows.click`) — click a UI element by selector or context key
- **WaitTool** (`windows.wait`) — poll until a UI element appears (with timeout)
- **DelayTool** (`windows.delay`) — pause execution for a fixed duration
- **ScreenshotTool** (`windows.screenshot`) — capture the screen or a window to a file
- **InputTextTool** (`windows.input_text`) — type text, key combos, or mixed (e.g. `"Hello"`, `"CTRL+S"`, `"[+CTRL]A[-CTRL]"`)
- **SetTextTool** (`windows.set_text`) — replace a UI element's text programmatically (ValuePattern / WM_SETTEXT)
- **GetElementTool** (`windows.get_element`) — read a UI element's attributes as a dict

All UI tools accept optional `pid` (or a `ProcessHandle`) to scope element search to a specific window.

## Custom Tools

Create tools from simple async functions:

```python
from smithy import Smithy, tool
from smithy.core.context import ExecutionContext


@tool("greet", description="Greet a person")
async def greet(config: dict, ctx: ExecutionContext) -> dict:
    name = config.get("name", "World")
    return {"message": f"Hello, {name}!"}


bot = Smithy(tools=[greet])


async def main() -> None:
    result = await bot.call("greet", name="Alice")
    print(result["message"])  # Hello, Alice!


asyncio.run(main())
```

## Error Handling

```python
from smithy.core.errors import InvalidInput, ElementNotFound, PlatformError

try:
    await bot.click(app, name="Nonexistent")
except ElementNotFound:
    print("Element not found")
except PlatformError as e:
    print(f"Platform error: {e}")
```

## Selector Capture

A dev utility for inspecting UI elements at screen coordinates and generating tool configs:

```bash
pip install smithy[capture]

# Single capture mode
python -m smithy.windows.tools.selector_capture single -o selectors.json

# Series mode — auto-record clicks and typing
python -m smithy.windows.tools.selector_capture series -o recording.json

# Interactive record mode
python -m smithy.windows.tools.selector_capture record -o flow.json
```

## Install

```bash
pip install smithy               # core (no deps)
pip install smithy[windows]     # Windows UIA tools
pip install smithy[capture]      # selector capture (pynput + pyperclip)
pip install smithy[all]          # everything
pip install -e ".[dev]"          # development
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

pytest                    # run tests
ruff check src/ tests/    # linter
mypy src/smithy --strict  # type check
```

## Project Structure

```
src/smithy/
├── __init__.py          — Public API: Smithy, ProcessHandle, Tool, errors
├── facade.py            — Smithy facade (async tool dispatch)
├── core/
│   ├── tool.py          — Tool protocol, AbstractTool, @tool decorator
│   ├── registry.py      — ToolRegistry (name → tool dispatch)
│   ├── context.py       — ExecutionContext (scoped variable storage)
│   └── errors.py        — Error hierarchy (ToolError, ElementNotFound, etc.)
└── windows/
    ├── element.py       — SafeUIElement (thread-safe COM wrapper)
    ├── selector.py      — ElementSelector (UIA tree search)
    └── tools/
        ├── process.py          — ProcessTool
        ├── find.py             — FindTool
        ├── click.py            — ClickTool
        ├── wait.py             — WaitTool
        ├── delay.py            — DelayTool
        ├── screenshot.py       — ScreenshotTool
        ├── input_text.py       — InputTextTool
        ├── set_text.py         — SetTextTool
        ├── get_element.py      — GetElementTool
        ├── _resolve.py         — Shared element resolution helper
        └── selector_capture/   — Dev tool for UI inspection
```

## Examples

- [`examples/basic_bot.py`](examples/basic_bot.py) — Launch Notepad and interact with its UI
- [`examples/custom_tool.py`](examples/custom_tool.py) — Create and use custom tools

## License

MIT
