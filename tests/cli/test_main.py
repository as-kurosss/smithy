"""Tests for smithy.cli.main — validate and run commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from smithy.cli.main import cmd_validate, main


def _write_robot(tmp_path: Path, robot: dict) -> Path:
    """Write a robot JSON file and return the path."""
    p = tmp_path / "robot.json"
    p.write_text(json.dumps(robot), encoding="utf-8")
    return p


class TestValidate:
    def test_valid_robot(self, tmp_path: Path) -> None:
        robot = {
            "name": "Test",
            "version": "1.0",
            "steps": [{"action": "http.request", "params": {}}],
        }
        path = _write_robot(tmp_path, robot)
        cmd_validate(path)

    def test_invalid_json(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text("not json", encoding="utf-8")
        with pytest.raises(SystemExit, match="1"):
            cmd_validate(p)

    def test_missing_name(self, tmp_path: Path) -> None:
        robot = {"version": "1.0", "steps": []}
        path = _write_robot(tmp_path, robot)
        with pytest.raises(SystemExit, match="1"):
            cmd_validate(path)


class TestMainCLI:
    def test_validate_command(self, tmp_path: Path) -> None:
        robot = {
            "name": "CLI Test",
            "version": "1.0",
            "steps": [],
        }
        path = _write_robot(tmp_path, robot)
        main(["validate", str(path)])

    def test_no_command_exits(self) -> None:
        with pytest.raises(SystemExit):
            main([])

    def test_unknown_command_exits(self) -> None:
        with pytest.raises(SystemExit):
            main(["unknown"])
