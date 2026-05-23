"""Tests for the format corrector: sample paper correction."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from pathlib import Path

from paper_format_corrector.app import PaperFormatCorrector


def test_sample_paper_correction(sample_paper_path, template_path, config, tmp_path):
    """Correct a sample paper and verify the report indicates real work was done."""
    output_path = str(tmp_path / "formatted_sample.docx")

    corrector = PaperFormatCorrector.__new__(PaperFormatCorrector)
    corrector.config = config
    corrector.template_path = template_path
    from paper_format_corrector.core.format_corrector import FormatCorrector
    from paper_format_corrector.core.format_exporter import FormatExporter
    from paper_format_corrector.infra.logger import Logger
    from paper_format_corrector.quality.diff_reporter import DiffReporter
    from paper_format_corrector.quality.quality_scorer import QualityScorer
    from paper_format_corrector.quality.rule_engine import RuleEngine

    corrector.corrector = FormatCorrector(template_path, config)
    corrector.exporter = FormatExporter()
    corrector.scorer = QualityScorer(config)
    corrector.diff_reporter = DiffReporter()
    corrector.rule_engine = RuleEngine()
    corrector.logger = Logger(level="WARNING")

    report = corrector.process_single(sample_paper_path, output_path)

    assert report is not None, "process_single should return a report"
    assert report["paragraphs_corrected"] > 0, "Should correct at least some paragraphs"
    assert report["headings_fixed"] > 0, "Should fix at least some headings"
    assert report["body_fixed"] > 0, "Should fix at least some body paragraphs"
    assert Path(output_path).exists(), "Output file should be created"


def test_sample_paper_quality_score(sample_paper_path, template_path, config, tmp_path):
    """Run quality scoring on a corrected paper."""
    output_path = str(tmp_path / "scored_sample.docx")

    corrector = PaperFormatCorrector.__new__(PaperFormatCorrector)
    corrector.config = config
    corrector.template_path = template_path
    from paper_format_corrector.core.format_corrector import FormatCorrector
    from paper_format_corrector.core.format_exporter import FormatExporter
    from paper_format_corrector.infra.logger import Logger
    from paper_format_corrector.quality.diff_reporter import DiffReporter
    from paper_format_corrector.quality.quality_scorer import QualityScorer
    from paper_format_corrector.quality.rule_engine import RuleEngine

    corrector.corrector = FormatCorrector(template_path, config)
    corrector.exporter = FormatExporter()
    corrector.scorer = QualityScorer(config)
    corrector.diff_reporter = DiffReporter()
    corrector.rule_engine = RuleEngine()
    corrector.logger = Logger(level="WARNING")

    report = corrector.process_single(sample_paper_path, output_path, score=True)

    assert report is not None
    assert "quality_score" in report, "Report should include quality_score when score=True"
    assert isinstance(report["quality_score"], (int, float)), "Quality score should be numeric"
    assert 0 <= report["quality_score"] <= 100, "Quality score should be between 0 and 100"


def test_sample_paper_diff_report(sample_paper_path, template_path, config, tmp_path):
    """Generate a diff report for a corrected paper."""
    output_path = str(tmp_path / "diff_sample.docx")

    corrector = PaperFormatCorrector.__new__(PaperFormatCorrector)
    corrector.config = config
    corrector.template_path = template_path
    from paper_format_corrector.core.format_corrector import FormatCorrector
    from paper_format_corrector.core.format_exporter import FormatExporter
    from paper_format_corrector.infra.logger import Logger
    from paper_format_corrector.quality.diff_reporter import DiffReporter
    from paper_format_corrector.quality.quality_scorer import QualityScorer
    from paper_format_corrector.quality.rule_engine import RuleEngine

    corrector.corrector = FormatCorrector(template_path, config)
    corrector.exporter = FormatExporter()
    corrector.scorer = QualityScorer(config)
    corrector.diff_reporter = DiffReporter()
    corrector.rule_engine = RuleEngine()
    corrector.logger = Logger(level="WARNING")

    report = corrector.process_single(sample_paper_path, output_path, diff=True)

    assert report is not None
    diff_path = Path(output_path).with_suffix(".diff.html")
    assert diff_path.exists(), "Diff HTML report should be generated"
