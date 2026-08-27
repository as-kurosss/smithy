"""Basic RPA bot example — launch Notepad and interact with it.

Requires: pip install smithy[windows]
"""

import asyncio

from smithy import Smithy
from smithy.windows.tools.click import ClickTool
from smithy.windows.tools.find import FindTool
from smithy.windows.tools.process import ProcessTool

bot = Smithy(tools=[ProcessTool(), FindTool(), ClickTool()])


async def main() -> None:
    # Launch Notepad — returns ProcessHandle with PID
    app = await bot.process("notepad.exe")

    # Find and click UI elements — PID auto-filters to our app
    await bot.find(app, name="Untitled - Notepad")
    await bot.click(app, name="File")
    await bot.click(app, name="Save As...")

    print(f"Notepad launched with PID: {app.pid}")


if __name__ == "__main__":
    asyncio.run(main())
