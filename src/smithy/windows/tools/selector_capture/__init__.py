"""Selector capture — inspect UIA elements at screen coordinates.

Public API::

    from smithy.windows.tools.selector_capture import (
        BestSelector,
        CaptureRecord,
        PathNode,
        capture_at_point,
        path_to_dicts,
    )
"""

from smithy.windows.tools.selector_capture.capture import (
    BestSelector,
    CaptureRecord,
    PathNode,
    capture_at_point,
    path_to_dicts,
)

__all__ = [
    "BestSelector",
    "CaptureRecord",
    "PathNode",
    "capture_at_point",
    "path_to_dicts",
]
