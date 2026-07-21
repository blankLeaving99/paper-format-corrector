"""Document-related domain events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DocumentCorrected:
    """Event raised when a document has been successfully corrected."""

    input_path: str
    output_path: str
    report: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def paragraphs_corrected(self) -> int:
        return self.report.get("paragraphs_corrected", 0)


@dataclass(frozen=True)
class DocumentFailed:
    """Event raised when document correction fails."""

    input_path: str
    error: str
    timestamp: datetime = field(default_factory=datetime.now)
