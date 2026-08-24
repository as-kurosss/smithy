"""Tests for smithy.engine.robot — Robot and Step Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from smithy.engine.robot import Robot, Step


class TestStep:
    def test_minimal_step(self) -> None:
        step = Step(action="windows.click", params={"selector": {"name": "OK"}})
        assert step.action == "windows.click"
        assert step.params == {"selector": {"name": "OK"}}
        assert step.outputs is None
        assert step.stop_on_error is True

    def test_step_with_outputs(self) -> None:
        step = Step(
            action="windows.process",
            params={"action": "start", "path": "notepad.exe"},
            outputs={"pid": "notepad_pid"},
        )
        assert step.outputs == {"pid": "notepad_pid"}

    def test_step_stop_on_error_false(self) -> None:
        step = Step(action="http.request", params={}, stop_on_error=False)
        assert step.stop_on_error is False

    def test_step_from_dict(self) -> None:
        d = {"action": "test", "params": {"a": 1}}
        step = Step(**d)
        assert step.action == "test"
        assert step.params == {"a": 1}

    def test_step_missing_action_raises(self) -> None:
        with pytest.raises(ValidationError):
            Step(params={})  # type: ignore[call-arg]

    def test_step_params_default_empty(self) -> None:
        step = Step(action="noop")
        assert step.params == {}


class TestRobot:
    def test_minimal_robot(self) -> None:
        robot = Robot(name="Test", version="1.0", steps=[])
        assert robot.name == "Test"
        assert robot.version == "1.0"
        assert robot.steps == []

    def test_robot_with_steps(self) -> None:
        steps = [
            Step(action="a", params={}),
            Step(action="b", params={"x": 1}),
        ]
        robot = Robot(name="R", version="2.0", steps=steps)
        assert len(robot.steps) == 2
        assert robot.steps[0].action == "a"

    def test_robot_from_dict(self) -> None:
        d = {
            "name": "MyBot",
            "version": "1.0",
            "steps": [
                {"action": "click", "params": {"selector": {"name": "OK"}}},
            ],
        }
        robot = Robot(**d)
        assert robot.name == "MyBot"
        assert len(robot.steps) == 1

    def test_robot_from_json_string(self) -> None:
        j = '{"name":"J","version":"1","steps":[{"action":"x","params":{}}]}'
        robot = Robot.model_validate_json(j)
        assert robot.name == "J"
        assert len(robot.steps) == 1

    def test_robot_missing_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            Robot(version="1.0", steps=[])  # type: ignore[call-arg]

    def test_robot_missing_steps_raises(self) -> None:
        with pytest.raises(ValidationError):
            Robot(name="X", version="1.0")  # type: ignore[call-arg]

    def test_robot_roundtrip_json(self) -> None:
        robot = Robot(
            name="R",
            version="1.0",
            steps=[Step(action="a", params={"k": "v"}, outputs={"out": "var"})],
        )
        j = robot.model_dump_json()
        robot2 = Robot.model_validate_json(j)
        assert robot2.name == robot.name
        assert len(robot2.steps) == 1
        assert robot2.steps[0].outputs == {"out": "var"}
