"""ProcessTool — manage Windows processes (start, stop, sleep)."""

from __future__ import annotations

import asyncio
import subprocess
from typing import Any

from smithy.core.context import ExecutionContext
from smithy.core.errors import InvalidInput, PlatformError
from smithy.core.tool import AbstractTool

# Whitelist of allowed executables (case-insensitive).
# cmd.exe and powershell.exe intentionally excluded (arbitrary command execution).
_ALLOWED_COMMANDS: set[str] = {
    "notepad.exe",
    "calc.exe",
    "mspaint.exe",
    "explorer.exe",
    "write.exe",
    "wordpad.exe",
}


def _is_command_allowed(cmd: str) -> bool:
    """Check if the executable is in the allowlist."""
    import os

    name = os.path.basename(cmd).lower()
    return name in _ALLOWED_COMMANDS


class ProcessTool(AbstractTool):
    """Manage Windows processes: start, stop, or sleep."""

    @property
    def name(self) -> str:
        return "windows.process"

    @property
    def description(self) -> str:
        return "Manages Windows processes: start, stop, or sleep"

    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["start", "stop", "sleep"]},
                "command": {
                    "type": "string",
                    "description": "Executable path",
                },
                "args": {"type": "array", "items": {"type": "string"}},
                "working_dir": {"type": "string"},
                "pid": {"type": "integer", "description": "Process ID to stop"},
                "name": {"type": "string", "description": "Process image name to stop"},
                "duration_ms": {"type": "integer", "minimum": 0},
                "delay_before_ms": {"type": "integer", "minimum": 0},
                "delay_after_ms": {"type": "integer", "minimum": 0},
            },
            "required": ["action"],
        }

    async def execute(
        self,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> Any:
        action = config.get("action", "").lower()

        # Optional delay before
        delay_before = config.get("delay_before_ms", 0)
        if delay_before and delay_before > 0:
            await asyncio.sleep(delay_before / 1000)

        try:
            if action == "start":
                result = await _action_start(config)
            elif action == "stop":
                result = await _action_stop(config)
            elif action == "sleep":
                result = await _action_sleep(config)
            else:
                raise InvalidInput(
                    f"Unknown process action: {action}",
                    param="action",
                    input_value=action,
                )
        except (InvalidInput, PlatformError):
            raise
        except Exception as exc:
            raise PlatformError(
                f"Process action '{action}' failed",
                source=exc,
            ) from exc

        # Optional delay after (only on success)
        delay_after = config.get("delay_after_ms", 0)
        if delay_after and delay_after > 0:
            await asyncio.sleep(delay_after / 1000)

        return result


async def _action_start(config: dict[str, Any]) -> dict[str, Any]:
    """Start a new process."""
    command = config.get("command")
    if not command:
        raise InvalidInput(
            "Missing 'command' for start action",
            param="command",
        )

    if not _is_command_allowed(command):
        raise InvalidInput(
            f"Command '{command}' is not in the allowed list",
            param="command",
            input_value=command,
        )

    args = config.get("args", [])
    working_dir = config.get("working_dir")

    loop = asyncio.get_running_loop()

    def _start() -> int:
        cmd = [command] + args
        proc = subprocess.Popen(
            cmd,
            cwd=working_dir,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        return proc.pid

    pid = await loop.run_in_executor(None, _start)
    return {"status": "started", "pid": pid}


async def _action_stop(config: dict[str, Any]) -> dict[str, Any]:
    """Stop a process by PID or name."""
    pid = config.get("pid")
    name = config.get("name")

    if pid is None and name is None:
        raise InvalidInput(
            "Must provide 'pid' or 'name' for stop action",
        )

    loop = asyncio.get_running_loop()

    def _stop_by_pid(pid: int) -> None:
        result = subprocess.run(
            ["taskkill", "/F", "/PID", str(pid)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise PlatformError(
                f"taskkill for pid {pid} failed: {result.stderr}",
            )

    def _stop_by_name(name: str) -> None:
        result = subprocess.run(
            ["taskkill", "/F", "/IM", name],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise PlatformError(
                f"taskkill for {name} failed: {result.stderr}",
            )

    if pid is not None:
        await loop.run_in_executor(None, _stop_by_pid, pid)
        return {"status": "stopped", "method": "pid", "pid": pid}

    # name is guaranteed non-None here (checked above)
    assert name is not None
    await loop.run_in_executor(None, _stop_by_name, name)
    return {"status": "stopped", "method": "name", "name": name}


async def _action_sleep(config: dict[str, Any]) -> dict[str, Any]:
    """Sleep for duration_ms milliseconds."""
    duration_ms = config.get("duration_ms")
    if duration_ms is None:
        raise InvalidInput(
            "Missing 'duration_ms' for sleep action",
            param="duration_ms",
        )

    await asyncio.sleep(duration_ms / 1000)
    return {"status": "slept", "duration_ms": duration_ms}
