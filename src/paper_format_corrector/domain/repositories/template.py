"""Abstract template repository interface.

Defines the contract for template persistence operations.
Implementations should be in infrastructure/ layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class TemplateRepository(ABC):
    """Abstract interface for template storage and retrieval."""

    @abstractmethod
    def save(self, template_name: str, config: dict[str, Any]) -> None:
        """Save a template configuration."""
        ...

    @abstractmethod
    def find_by_name(self, template_name: str) -> dict[str, Any] | None:
        """Find a template by name."""
        ...

    @abstractmethod
    def find_all(self) -> list[dict[str, Any]]:
        """List all templates."""
        ...

    @abstractmethod
    def delete(self, template_name: str) -> bool:
        """Delete a template. Returns True if deleted."""
        ...

    @abstractmethod
    def exists(self, template_name: str) -> bool:
        """Check if a template exists."""
        ...
