"""Abstract document repository interface.

Defines the contract for document persistence operations.
Implementations should be in infrastructure/ layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class DocumentRepository(ABC):
    """Abstract interface for document storage and retrieval."""

    @abstractmethod
    def save(self, document_id: str, data: dict[str, Any]) -> None:
        """Save a document record."""
        ...

    @abstractmethod
    def find_by_id(self, document_id: str) -> dict[str, Any] | None:
        """Find a document by its ID."""
        ...

    @abstractmethod
    def find_all(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """List documents with pagination."""
        ...

    @abstractmethod
    def delete(self, document_id: str) -> bool:
        """Delete a document record. Returns True if deleted."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Return total number of documents."""
        ...
