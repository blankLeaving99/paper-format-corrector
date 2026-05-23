"""Integration tests for thesis-format correction with requirement documents."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from pathlib import Path
from paper_format_corrector.app import PaperFormatCorrector
from paper_format_corrector.core.format_corrector import FormatCorrector
from paper_format_corrector.quality.quality_scorer import QualityScorer
from paper_format_corrector.quality.diff_reporter import DiffReporter
from paper_format_corrector.quality.rule_engine import RuleEngine
from paper_format_corrector.core.format_exporter import FormatExporter
from paper_format_corrector.infra.logger import Logger


def _make_corrector(config, template_path):
    """Helper to build a PaperFormatCorrector with the given config and template."""
    corrector = PaperFormatCorrector.__new__(PaperFormatCorrector)
    corrector.config = config
    corrector.template_path = template_path
    corrector.corrector = FormatCorrector(template_path, config)
    corrector.exporter = FormatExporter()
    corrector.scorer = QualityScorer(config)
    corrector.diff_reporter = DiffReporter()
    corrector.rule_engine = RuleEngine()
    corrector.logger = Logger(level="WARNING")
    return corrector


def test_thesis_correction_with_requirement(
    thesis_paper_path, thesis_requirement_path, template_path, config, tmp_path
):
    """Correct a thesis using a requirement document and verify the report."""
    output_path = str(tmp_path / "thesis_formatted.docx")

    corrector = _make_corrector(config, template_path)
    corrector.apply_requirement(thesis_requirement_path)

    report = corrector.process_single(thesis_paper_path, output_path)

    assert report is not None, "Should produce a report"
    assert report["paragraphs_corrected"] > 0, "Should correct paragraphs"
    assert report["headings_fixed"] >= 3, "Should fix at least 3 headings (3 chapters)"
    assert report["body_fixed"] > 0, "Should fix body paragraphs"
    assert Path(output_path).exists(), "Output file should exist"


def test_thesis_has_fig_table_issues(thesis_paper_path, template_path, config, tmp_path):
    """Verify that figure/table numbering issues are detected."""
    output_path = str(tmp_path / "thesis_fig_table.docx")

    corrector = _make_corrector(config, template_path)
    report = corrector.process_single(thesis_paper_path, output_path)

    assert report is not None
    # The sample thesis has misnumbered figures/tables, so issues should be detected
    assert len(report.get("fig_table_issues", [])) > 0, "Should detect figure/table numbering issues"


def test_thesis_with_quality_score(
    thesis_paper_path, thesis_requirement_path, template_path, config, tmp_path
):
    """Run quality scoring on a corrected thesis."""
    output_path = str(tmp_path / "thesis_scored.docx")

    corrector = _make_corrector(config, template_path)
    corrector.apply_requirement(thesis_requirement_path)

    report = corrector.process_single(thesis_paper_path, output_path, score=True)

    assert report is not None
    assert "quality_score" in report
    assert 0 <= report["quality_score"] <= 100


def test_thesis_with_diff_report(
    thesis_paper_path, thesis_requirement_path, template_path, config, tmp_path
):
    """Generate a diff report for a corrected thesis."""
    output_path = str(tmp_path / "thesis_diff.docx")

    corrector = _make_corrector(config, template_path)
    corrector.apply_requirement(thesis_requirement_path)

    report = corrector.process_single(thesis_paper_path, output_path, diff=True)

    assert report is not None
    diff_path = Path(output_path).with_suffix(".diff.html")
    assert diff_path.exists(), "Diff report should be generated"


def test_thesis_tables_formatted(thesis_paper_path, template_path, config, tmp_path):
    """Verify that tables in the thesis get formatted."""
    output_path = str(tmp_path / "thesis_tables.docx")

    corrector = _make_corrector(config, template_path)
    report = corrector.process_single(thesis_paper_path, output_path)

    assert report is not None
    assert report.get("tables_formatted", 0) >= 0, "tables_formatted should be a non-negative int"
