"""Variable interpolation — {{var}} substitution in strings and structures."""

from __future__ import annotations

import re
from typing import Any

from smithy.core.context import ExecutionContext

_VAR_RE = re.compile(r"\{\{(\w+)\}\}")


def interpolate(template: str, ctx: ExecutionContext) -> str:
    """Replace {{var}} placeholders in a string using the execution context.

    Missing variables are left as-is (e.g. ``{{missing}}`` stays).
    Non-string values are coerced via ``str()``.
    """

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        cv = ctx.get(key)
        if cv is None:
            return match.group(0)
        return str(cv.value)

    return _VAR_RE.sub(_replace, template)


def interpolate_value(value: Any, ctx: ExecutionContext) -> Any:
    """Recursively interpolate {{var}} placeholders in a value.

    - ``str`` → run through :func:`interpolate`
    - ``dict`` → interpolate each value recursively
    - ``list`` → interpolate each element recursively
    - everything else → returned unchanged
    """
    if isinstance(value, str):
        return interpolate(value, ctx)
    if isinstance(value, dict):
        return {k: interpolate_value(v, ctx) for k, v in value.items()}
    if isinstance(value, list):
        return [interpolate_value(item, ctx) for item in value]
    return value
