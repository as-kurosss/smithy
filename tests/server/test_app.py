"""Tests for smithy.server.app — FastAPI REST endpoints."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from smithy.core.registry import ToolRegistry
from smithy.server.app import app, init_server

# --- Helpers ---


def _make_tool(name: str, return_value: Any = "ok") -> AsyncMock:
    tool = AsyncMock()
    tool.name = name
    tool.execute.return_value = return_value
    return tool


@pytest.fixture(autouse=True)
def setup_server() -> None:
    """Initialize the server with a fresh registry for each test."""
    reg = ToolRegistry()
    reg.register(_make_tool("stub.tool"))
    init_server(reg)


# --- Tests ---


class TestHealth:
    @pytest.mark.asyncio
    async def test_health(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestParseRobot:
    @pytest.mark.asyncio
    async def test_parse_valid_robot(self) -> None:
        robot_json = json.dumps({
            "name": "Test",
            "version": "1.0",
            "steps": [{"action": "stub.tool", "params": {}}],
        })
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/parse-robot", json={"robot_json": robot_json})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test"
        assert len(data["steps"]) == 1

    @pytest.mark.asyncio
    async def test_parse_invalid_json(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/parse-robot", json={"robot_json": "not json"})
        assert resp.status_code == 400


class TestRunRobot:
    @pytest.mark.asyncio
    async def test_run_robot(self) -> None:
        robot = {
            "name": "Test",
            "version": "1.0",
            "steps": [{"action": "stub.tool", "params": {}}],
        }
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/run-robot", json={"robot": robot})
        assert resp.status_code == 200
        assert "job_id" in resp.json()

    @pytest.mark.asyncio
    async def test_run_robot_invalid(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/run-robot", json={"robot": {"bad": True}})
        assert resp.status_code == 400


class TestGetJob:
    @pytest.mark.asyncio
    async def test_get_existing_job(self) -> None:
        robot = {
            "name": "Test",
            "version": "1.0",
            "steps": [{"action": "stub.tool", "params": {}}],
        }
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/run-robot", json={"robot": robot})
            job_id = resp.json()["job_id"]
            resp = await client.get(f"/job/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == job_id
        assert data["robot_name"] == "Test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_job(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/job/999")
        assert resp.status_code == 404


class TestHistory:
    @pytest.mark.asyncio
    async def test_empty_history(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/history")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_history_after_submit(self) -> None:
        robot = {
            "name": "R",
            "version": "1.0",
            "steps": [{"action": "stub.tool", "params": {}}],
        }
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.post("/run-robot", json={"robot": robot})
            resp = await client.get("/history")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


class TestCancelJob:
    @pytest.mark.asyncio
    async def test_cancel_nonexistent(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/cancel-job/999")
        assert resp.status_code == 404


class TestContext:
    @pytest.mark.asyncio
    async def test_context_nonexistent(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/context/999")
        assert resp.status_code == 200
        assert resp.json() == {}


class TestDebugEndpoints:
    @pytest.mark.asyncio
    async def test_set_breakpoints(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/set-breakpoints/0", json={"breakpoints": [0, 2]}
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_resume(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/resume/0")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_step_over(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/step-over/0")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_debug_status(self) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/debug-status/0")
        assert resp.status_code == 200
        assert resp.json()["is_paused"] is False
