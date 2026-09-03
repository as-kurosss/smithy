"""CLI entry point for selector-capture.

Usage::

    python -m smithy.windows.tools.selector_capture single -o selectors.json
    python -m smithy.windows.tools.selector_capture series -o recording.json
    python -m smithy.windows.tools.selector_capture record -o flow.json
"""

from __future__ import annotations

import argparse
import logging
import sys

from smithy.windows.tools.selector_capture.generate import ToolType
from smithy.windows.tools.selector_capture.recorder import (
    run_record_mode,
    run_series_mode,
    run_single_mode,
)


def main(argv: list[str] | None = None) -> None:
    """Parse CLI arguments and dispatch to the appropriate capture mode."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )

    parser = argparse.ArgumentParser(
        prog="selector-capture",
        description="Capture UI element selectors and generate flow configs",
    )
    parser.add_argument(
        "-B",
        "--backend",
        default="windows",
        help="Platform backend (default: windows)",
    )

    sub = parser.add_subparsers(dest="command", help="Capture mode")

    # ── single ──
    p_single = sub.add_parser("single", help="Capture a single element and exit")
    p_single.add_argument("-o", "--output", default="selectors.json", help="Output JSON file")
    p_single.add_argument("-d", "--description", help="Description for the capture")
    p_single.add_argument(
        "-t",
        "--tool",
        choices=[t.value for t in ToolType],
        default="click",
        help="Tool type for config generation (default: click)",
    )
    p_single.add_argument("--text", default="", help="Text for input_text / set_text")
    p_single.add_argument(
        "--duration-ms",
        type=int,
        default=1000,
        help="Duration for wait tool (ms)",
    )
    p_single.add_argument("--clip", action="store_true", help="Copy config to clipboard")

    # ── series ──
    p_series = sub.add_parser(
        "series",
        help="Record all clicks & inputs; Ctrl+Shift+F2 to stop",
    )
    p_series.add_argument("-o", "--output", default="recording.json", help="Output JSON file")

    # ── record ──
    p_record = sub.add_parser(
        "record",
        help="Interactive: CTRL to capture, prompts for tool/params",
    )
    p_record.add_argument("-o", "--output", default="flow.json", help="Output JSON file")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "single":
        tool_type = ToolType(args.tool)
        run_single_mode(
            output=args.output,
            description=args.description,
            tool_type=tool_type,
            text=args.text,
            duration_ms=args.duration_ms,
            clip=args.clip,
        )
    elif args.command == "series":
        run_series_mode(output=args.output)
    elif args.command == "record":
        run_record_mode(output=args.output)
