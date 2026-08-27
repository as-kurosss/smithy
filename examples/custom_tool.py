"""Custom tool example — create tools from simple functions.

Requires: pip install smithy
"""

import asyncio

from smithy import Smithy, tool
from smithy.core.context import ExecutionContext


@tool("greet", description="Greet a person by name")
async def greet(config: dict, ctx: ExecutionContext) -> dict:
    name = config.get("name", "World")
    return {"message": f"Hello, {name}!"}


@tool("add", description="Add two numbers")
async def add(config: dict, ctx: ExecutionContext) -> dict:
    a = config.get("a", 0)
    b = config.get("b", 0)
    return {"result": a + b}


bot = Smithy(tools=[greet, add])


async def main() -> None:
    # Use custom tools via call()
    greeting = await bot.call("greet", name="Alice")
    print(greeting["message"])  # Hello, Alice!

    sum_result = await bot.call("add", a=3, b=5)
    print(sum_result["result"])  # 8


if __name__ == "__main__":
    asyncio.run(main())
