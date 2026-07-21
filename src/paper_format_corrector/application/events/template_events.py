"""Template-related domain events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class TemplateApplied:
    """Event raised when a template/preset is applied."""

    template_name: str
    preset_name: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class TemplateLoaded:
    """Event raised when a template is loaded from storage."""

    template_name: str
    source: str  # "preset", "file", "database"
    timestamp: datetime = field(default_factory=datetime.now)
