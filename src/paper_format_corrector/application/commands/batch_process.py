"""BatchProcess command - orchestrates batch document correction."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BatchProcessCommand:
    """Command to correct multiple documents in batch.

    Encapsulates all parameters needed for batch processing.
    """

    input_paths: list[str | Path]
    output_dir: str | Path
    preset: str | None = None
    requirement_path: str | None = None
    score: bool = False
    diff: bool = False
    config_overrides: dict[str, Any] | None = None

    def execute(self, corrector: Any) -> list[dict[str, Any]]:
        """Execute the batch correction command.

        Args:
            corrector: PaperFormatCorrector instance.

        Returns:
            List of correction report dictionaries.
        """
        results = []
        output_dir = Path(self.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for input_path in self.input_paths:
            input_p = Path(input_path)
            output_path = output_dir / f"{input_p.stem}_corrected{input_p.suffix}"
            try:
                report = corrector.process_single(
                    str(input_path),
                    str(output_path),
                    score=self.score,
                    diff=self.diff,
                )
                report["input_path"] = str(input_path)
                report["output_path"] = str(output_path)
                report["status"] = "success"
                results.append(report)
            except Exception as e:
                results.append({
                    "input_path": str(input_path),
                    "status": "error",
                    "error": str(e),
                })
        return results
