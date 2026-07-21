"""Report query - read-only operations for report generation and retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ReportQuery:
    """Query for generating reports from correction results.

    Read-only operation - does not modify system state.
    """

    report_data: dict[str, Any]
    output_format: str = "html"

    def execute(self, report_service: Any) -> str | None:
        """Execute the report query.

        Args:
            report_service: ReportService instance.

        Returns:
            Path to generated report, or None.
        """
        if self.output_format == "html":
            return report_service.generate_html_report(self.report_data)
        elif self.output_format == "pdf":
            return report_service.generate_pdf_report(self.report_data)
        return None
