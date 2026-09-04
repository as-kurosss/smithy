"""TOML robot config — load once in Init, fail fast, frozen afterwards.

The file replaces the legacy two-column Excel sheet: same idea (one config
per robot, values differ per environment), but diffable in git, typed, and
validated up front. Secrets never live here — only *references* to
orchestrator assets (names, GUIDs); values are fetched at runtime.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from smithy.core.errors import ConfigError

_MISSING = object()


class Config:
    """Immutable attribute-style view over a loaded TOML document.

    Nested tables become nested :class:`Config`, lists become tuples —
    nothing inside can be reassigned after loading. Access by attribute
    (``config.paths.workdir``) or by item (``config[\"paths\"][\"workdir\"]``).
    """

    __slots__ = ("_data",)

    def __init__(self, data: dict[str, Any]) -> None:
        object.__setattr__(self, "_data", data)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(f"Config is frozen; cannot set {name!r}")

    def __getattr__(self, name: str) -> Any:
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(f"Unknown config key: {name!r}") from None

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def __repr__(self) -> str:
        return f"Config({self._data!r})"

    def to_dict(self) -> dict[str, Any]:
        """Plain deep copy of the document (logging, debugging)."""
        return {key: _thaw(value) for key, value in self._data.items()}


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return Config({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Config):
        return value.to_dict()
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _lookup(config: Config, dotted: str) -> Any:
    current: Any = config
    for part in dotted.split("."):
        if isinstance(current, Config) and part in current:
            current = current[part]
        else:
            return _MISSING
    return current


def load_config(
    path: str | Path,
    *,
    required: tuple[str, ...] | list[str] = (),
    must_exist: tuple[str, ...] | list[str] = (),
) -> Config:
    """Load *path* as TOML and validate it.

    Raises one :class:`ConfigError` listing *every* problem at once —
    the robot fails in Init, never mid-run. *required* are dotted keys
    that must be present (``\"robot.queue\"``); *must_exist* are dotted
    keys whose values must be existing filesystem paths.
    """
    file = Path(path)
    try:
        raw = file.read_bytes()
    except OSError as exc:
        raise ConfigError(f"Cannot read config file: {file}", input_value=str(file)) from exc
    try:
        document = tomllib.loads(raw.decode("utf-8"))
    except ValueError as exc:
        raise ConfigError(f"Invalid TOML in {file}: {exc}", input_value=str(file)) from exc
    frozen = _freeze(document)
    assert isinstance(frozen, Config)
    problems: list[str] = []
    for key in required:
        if _lookup(frozen, key) is _MISSING:
            problems.append(f"missing required key: {key!r}")
    for key in must_exist:
        value = _lookup(frozen, key)
        if value is _MISSING:
            problems.append(f"missing path key: {key!r}")
        elif not isinstance(value, (str, Path)) or not Path(value).exists():
            problems.append(f"path does not exist: {key!r} = {value!r}")
    if problems:
        raise ConfigError(
            f"Invalid config {file}:\n" + "\n".join(f"  - {item}" for item in problems),
            input_value=str(file),
        )
    return frozen
