"""ElementSelector — builder-style selector for finding Windows UI elements."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from smithy.core.errors import ElementNotFound, PlatformError


@dataclass
class ElementSelector:
    """Builder-style selector for finding Windows UI elements.

    Uses ``uiautomation.FindControl`` with a compare function.
    """
    pid: int | None = None
    name: str | None = None
    automation_id: str | None = None
    control_type: str | None = None
    class_name: str | None = None

    def with_pid(self, pid: int) -> ElementSelector:
        """Filter by process ID."""
        self.pid = pid
        return self

    def with_name(self, name: str) -> ElementSelector:
        """Filter by element name (exact match)."""
        self.name = name
        return self

    def with_automation_id(self, automation_id: str) -> ElementSelector:
        """Filter by automation ID."""
        self.automation_id = automation_id
        return self

    def with_control_type(self, control_type: str) -> ElementSelector:
        """Filter by control type name (e.g. Button, Edit, Window)."""
        self.control_type = control_type
        return self

    def with_class_name(self, class_name: str) -> ElementSelector:
        """Filter by class name."""
        self.class_name = class_name
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dict of non-None fields (for JSON serialization)."""
        d: dict[str, Any] = {}
        if self.pid is not None:
            d["pid"] = self.pid
        if self.name is not None:
            d["name"] = self.name
        if self.automation_id is not None:
            d["automation_id"] = self.automation_id
        if self.control_type is not None:
            d["control_type"] = self.control_type
        if self.class_name is not None:
            d["class_name"] = self.class_name
        return d

    def find_first(self, root: Any, automation: Any) -> Any:
        """Find the first matching element under ``root``.

        Args:
            root: A ``uiautomation`` control to search under.
            automation: The ``uiautomation.uiautomation`` module.

        Returns:
            The first matching control.

        Raises:
            ElementNotFound: If no element matches.
            PlatformError: If the UIA call fails.
        """
        compare = self._build_compare()
        try:
            element = automation.FindControl(root, compare)
        except Exception as exc:
            raise PlatformError(
                "find_first failed",
                source=exc,
            ) from exc
        if element is None:
            raise ElementNotFound(
                "No element found matching selector",
                selector=self.to_dict(),
            )
        return element

    def find_from_desktop(self) -> Any:
        """Find the first matching element starting from the desktop root.

        Returns:
            The first matching control.

        Raises:
            ElementNotFound: If no element matches.
            PlatformError: If UIA init fails.
        """
        try:
            import uiautomation as auto

            root = auto.GetRootControl()
        except Exception as exc:
            raise PlatformError(
                "UIAutomation init failed",
                source=exc,
            ) from exc
        return self.find_first(root, auto.uiautomation)

    def _build_compare(self) -> Callable[[Any, int], bool]:
        """Build a compare function for FindControl."""
        # Capture values for the closure
        name = self.name
        automation_id = self.automation_id
        control_type = self.control_type
        class_name = self.class_name
        pid = self.pid

        ct_value = _parse_control_type(control_type) if control_type else None

        def compare(ctrl: Any, depth: int) -> bool:
            # Name has priority — if it matches, accept the element
            # regardless of class_name (class_name scopes the parent window,
            # but child elements have different ClassName values).
            if name is not None:
                return bool(ctrl.Name == name)
            # Without name, filter by other properties.
            if automation_id is not None and ctrl.AutomationId != automation_id:
                return False
            if ct_value is not None and ctrl.ControlType != ct_value:
                return False
            if class_name is not None and ctrl.ClassName != class_name:
                return False
            return not (pid is not None and ctrl.ProcessId != pid)

        return compare


# Control type string → integer mapping (matching Rust parse_control_type)
_CONTROL_TYPE_MAP: dict[str, int] = {
    "button": 50000,
    "calendar": 50001,
    "checkbox": 50002,
    "combobox": 50003,
    "edit": 50004,
    "hyperlink": 50005,
    "image": 50006,
    "listitem": 50007,
    "list": 50008,
    "menu": 50009,
    "menubar": 50010,
    "menuitem": 50011,
    "progressbar": 50012,
    "radiobutton": 50013,
    "scrollbar": 50014,
    "slider": 50015,
    "spinner": 50016,
    "statusbar": 50017,
    "tab": 50018,
    "tabitem": 50019,
    "toolbar": 50020,
    "tooltip": 50021,
    "tree": 50022,
    "treeitem": 50023,
    "custom": 50024,
    "group": 50025,
    "thumb": 50026,
    "datagrid": 50027,
    "dataitem": 50028,
    "document": 50029,
    "splitbutton": 50030,
    "window": 50031,
    "pane": 50032,
    "header": 50033,
    "headeritem": 50034,
    "table": 50035,
    "titlebar": 50036,
    "separator": 50037,
    "appbar": 50038,
    "text": 50004,  # alias for edit
}


def _parse_control_type(s: str) -> int | None:
    """Parse a control type string into its numeric UIA identifier."""
    return _CONTROL_TYPE_MAP.get(s.lower())
