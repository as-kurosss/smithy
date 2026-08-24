"""Smithy server entry point — python -m smithy [port]."""

from __future__ import annotations

import argparse

from smithy.engine.tools import default_registry
from smithy.server.app import app, init_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Smithy RPA server")
    parser.add_argument(
        "--port", type=int, default=9500, help="Port to listen on (default: 9500)"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)"
    )
    args = parser.parse_args()

    init_server(default_registry())

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
