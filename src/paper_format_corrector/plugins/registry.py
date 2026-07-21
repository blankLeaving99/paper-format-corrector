"""Plugin registry for discovering and loading plugins."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import FormatPlugin

_registry: dict[str, type[FormatPlugin]] = {}


def register(plugin_cls: type[FormatPlugin]) -> type[FormatPlugin]:
    """Register a plugin class."""
    _registry[plugin_cls.__name__] = plugin_cls
    return plugin_cls


def get(name: str) -> FormatPlugin | None:
    """Get a plugin instance by name."""
    cls = _registry.get(name)
    return cls() if cls else None


def list_plugins() -> list[str]:
    """List registered plugin names."""
    return list(_registry.keys())
