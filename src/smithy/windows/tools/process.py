"""ProcessTool — manage Windows processes (start, stop)."""

from __future__ import annotations

import asyncio
import os
import subprocess
from typing import Any

from smithy.core.errors import InvalidInput, PlatformError
from smithy.core.tool import AbstractTool

# Whitelist of allowed executables (case-insensitive).
# cmd.exe and powershell.exe intentionally excluded (arbitrary command execution).
_ALLOWED_COMMANDS: frozenset[str] = frozenset(
    {
        "notepad.exe",
        "calc.exe",
        "mspaint.exe",
        "explorer.exe",
        "write.exe",
        "wordpad.exe",
    }
)


def _is_command_allowed(cmd: str) -> bool:
    """Check if the executable is in the allowlist."""
    return os.path.basename(cmd).lower() in _ALLOWED_COMMANDS


class ProcessTool(AbstractTool):
    """Manage Windows processes: start or stop."""

    @property
    def name(self) -> str:
        return "windows.process"

    @property
    def description(self) -> str:
        return "Manages Windows processes: start or stop"

    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["start", "stop"]},
                "command": {
                    "type": "string",
                    "description": "Executable path",
                },
                "args": {"type": "array", "items": {"type": "string"}},
                "working_dir": {"type": "string"},
                "pid": {"type": "integer", "description": "Process ID to stop"},
                "name": {"type": "string", "description": "Process image name to stop"},
            },
            "required": ["action"],
        }

    async def execute(
        self,
        config: dict[str, Any],
    ) -> Any:
        raw_action = config.get("action", "")
        if not isinstance(raw_action, str):
            raise InvalidInput(
                "Invalid 'action': expected a string",
                param="action",
                input_value=raw_action,
            )
        action = raw_action.lower()

        try:
            if action == "start":
                return await _action_start(config)
            if action == "stop":
                return await _action_stop(config)
        except (InvalidInput, PlatformError):
            raise
        except Exception as exc:
            raise PlatformError(
                f"Process action '{action}' failed",
                source=exc,
            ) from exc

        raise InvalidInput(
            f"Unknown process action: {action}",
            param="action",
            input_value=action,
        )


async def _action_start(config: dict[str, Any]) -> dict[str, Any]:
    """Start a new process."""
    command = config.get("command")
    if not isinstance(command, str) or not command:
        raise InvalidInput(
            "Missing 'command' for start action",
            param="command",
            input_value=command,
        )

    if not _is_command_allowed(command):
        raise InvalidInput(
            f"Command '{command}' is not in the allowed list",
            param="command",
            input_value=command,
        )

    args = config.get("args", [])
    if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
        raise InvalidInput(
            "Invalid 'args': expected a list of strings",
            param="args",
            input_value=args,
        )
    working_dir = config.get("working_dir")
    if working_dir is not None and not isinstance(working_dir, str):
        raise InvalidInput(
            "Invalid 'working_dir': expected a string",
            param="working_dir",
            input_value=working_dir,
        )

    loop = asyncio.get_running_loop()

    def _start() -> int:
        proc = subprocess.Popen(
            [command, *args],
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
            param="pid",
        )
    if pid is not None and (isinstance(pid, bool) or not isinstance(pid, int)):
        raise InvalidInput(
            "Invalid 'pid': expected an integer",
            param="pid",
            input_value=pid,
        )
    if name is not None and (not isinstance(name, str) or not name):
        raise InvalidInput(
            "Invalid 'name': expected a non-empty string",
            param="name",
            input_value=name,
        )

    loop = asyncio.get_running_loop()

    if pid is not None:

        def _stop_by_pid() -> None:
            result = subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise PlatformError(
                    f"taskkill for pid {pid} failed: {result.stderr}",
                )

        await loop.run_in_executor(None, _stop_by_pid)
        return {"status": "stopped", "method": "pid", "pid": pid}

    if name is None:  # narrowed by the pid-branch above; explicit, not assert
        raise InvalidInput(
            "Must provide 'pid' or 'name' for stop action",
            param="name",
        )

    def _stop_by_name() -> None:
        result = subprocess.run(
            ["taskkill", "/F", "/IM", name],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise PlatformError(
                f"taskkill for {name} failed: {result.stderr}",
            )

    await loop.run_in_executor(None, _stop_by_name)
    return {"status": "stopped", "method": "name", "name": name}
