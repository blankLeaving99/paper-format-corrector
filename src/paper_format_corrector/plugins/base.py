"""Base plugin interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class FormatPlugin(ABC):
    """Base class for format correction plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""

    @property
    def version(self) -> str:
        return "1.0.0"

    @abstractmethod
    def apply(self, config: dict[str, Any]) -> dict[str, Any]:
        """Apply plugin-specific format rules."""
