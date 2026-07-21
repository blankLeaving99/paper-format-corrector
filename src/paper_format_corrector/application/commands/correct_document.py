"""CorrectDocument command - orchestrates single document correction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CorrectDocumentCommand:
    """Command to correct a single document's formatting.

    Encapsulates all parameters needed for document correction.
    """

    input_path: str | Path
    output_path: str | Path
    preset: str | None = None
    requirement_path: str | None = None
    score: bool = False
    diff: bool = False
    config_overrides: dict[str, Any] | None = None

    def execute(self, corrector: Any) -> dict[str, Any]:
        """Execute the correction command.

        Args:
            corrector: PaperFormatCorrector instance.

        Returns:
            Correction report dictionary.
        """
        return corrector.process_single(
            str(self.input_path),
            str(self.output_path),
            score=self.score,
            diff=self.diff,
        )
