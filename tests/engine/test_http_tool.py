"""Tests for smithy.engine.tools.http — HttpTool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from smithy.core.context import ExecutionContext
from smithy.core.errors import InvalidInput
from smithy.engine.tools.http import HttpTool


class TestHttpTool:
    def test_tool_metadata(self) -> None:
        tool = HttpTool()
        assert tool.name == "http.request"
        assert "HTTP" in tool.description or "http" in tool.description.lower()
        assert isinstance(tool.schema(), dict)

    @pytest.mark.asyncio
    async def test_get_request(self) -> None:
        tool = HttpTool()
        ctx = ExecutionContext.create()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = '{"ok": true}'
        mock_response.headers = {"content-type": "application/json"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("smithy.engine.tools.http.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = mock_client
            result = await tool.execute(
                {"url": "http://example.com", "method": "GET"},
                ctx,
            )

        assert result["status"] == 200
        assert result["body"] == '{"ok": true}'

    @pytest.mark.asyncio
    async def test_post_request(self) -> None:
        tool = HttpTool()
        ctx = ExecutionContext.create()
        mock_response = AsyncMock()
        mock_response.status_code = 201
        mock_response.text = '{"id": 1}'
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("smithy.engine.tools.http.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = mock_client
            result = await tool.execute(
                {
                    "url": "http://example.com/api",
                    "method": "POST",
                    "body": '{"name": "test"}',
                    "headers": {"Content-Type": "application/json"},
                },
                ctx,
            )

        assert result["status"] == 201

    @pytest.mark.asyncio
    async def test_missing_url_raises(self) -> None:
        tool = HttpTool()
        ctx = ExecutionContext.create()
        with pytest.raises(InvalidInput, match="url"):
            await tool.execute({"method": "GET"}, ctx)

    @pytest.mark.asyncio
    async def test_invalid_method_raises(self) -> None:
        tool = HttpTool()
        ctx = ExecutionContext.create()
        with pytest.raises(InvalidInput, match="method"):
            await tool.execute({"url": "http://x.com", "method": "PATCH"}, ctx)
