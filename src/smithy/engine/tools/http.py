"""HttpTool — HTTP request tool using httpx."""

from __future__ import annotations

from typing import Any

import httpx

from smithy.core.context import ExecutionContext
from smithy.core.errors import InvalidInput, PlatformError
from smithy.core.tool import AbstractTool


class HttpTool(AbstractTool):
    """Execute HTTP requests (GET, POST)."""

    @property
    def name(self) -> str:
        return "http.request"

    @property
    def description(self) -> str:
        return "Execute an HTTP request and return status, headers, and body."

    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "method": {"type": "string", "enum": ["GET", "POST"]},
                "body": {"type": "string"},
                "headers": {"type": "object"},
            },
            "required": ["url", "method"],
        }

    async def execute(
        self,
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> Any:
        url = config.get("url")
        if not url:
            raise InvalidInput("Missing required parameter: url", param="url")

        method = config.get("method", "GET").upper()
        if method not in ("GET", "POST"):
            raise InvalidInput(
                f"Unsupported HTTP method: {method}",
                param="method",
                input_value=method,
            )

        body = config.get("body")
        headers = config.get("headers", {})

        try:
            async with httpx.AsyncClient() as client:
                if method == "GET":
                    resp = await client.get(url, headers=headers)
                else:
                    resp = await client.post(url, content=body, headers=headers)

            return {
                "status": resp.status_code,
                "headers": dict(resp.headers),
                "body": resp.text,
            }
        except httpx.HTTPError as exc:
            raise PlatformError(
                f"HTTP request failed: {exc}",
                source=exc,
                input_value=url,
            ) from exc
