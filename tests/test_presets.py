"""Tests for the format preset system."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import pytest
import yaml
from pathlib import Path

from paper_format_corrector.infra.preset_loader import (
    list_presets,
    load_preset,
    get_preset_choices,
    format_preset_list,
)


def test_list_presets():
    """list_presets should return all preset files."""
    presets = list_presets()
    names = [p["name"] for p in presets]
    assert "ieee" in names, "Should include ieee preset"
    assert "nature" in names, "Should include nature preset"
    assert "science" in names, "Should include science preset"
    assert "apa" in names, "Should include apa preset"
    assert "chinese_thesis" in names, "Should include chinese_thesis preset"
    assert len(presets) >= 5


def test_get_preset_choices():
    """get_preset_choices should return a list of preset name strings."""
    choices = get_preset_choices()
    assert isinstance(choices, list)
    assert "ieee" in choices
    assert "chinese_thesis" in choices


def test_load_preset_valid():
    """Loading a valid preset should return a dict with format_rules."""
    for name in ["ieee", "nature", "science", "apa", "chinese_thesis"]:
        config = load_preset(name)
        assert isinstance(config, dict), f"[{name}] should return a dict"
        assert "format_rules" in config or "auto_detect" in config, \
            f"[{name}] should have format_rules or auto_detect"


def test_load_preset_has_font():
    """Each preset should define font settings."""
    for name in ["ieee", "nature", "science", "apa", "chinese_thesis"]:
        config = load_preset(name)
        font = config.get("format_rules", {}).get("font", {})
        assert font.get("english") is not None, f"[{name}] should define english font"


def test_load_preset_has_headings():
    """Each preset should define heading formats."""
    for name in ["ieee", "nature", "science", "apa", "chinese_thesis"]:
        config = load_preset(name)
        headings = config.get("format_rules", {}).get("headings", {})
        assert "heading1" in headings, f"[{name}] should define heading1"
        assert "heading2" in headings, f"[{name}] should define heading2"


def test_load_preset_has_body():
    """Each preset should define body text format."""
    for name in ["ieee", "nature", "science", "apa", "chinese_thesis"]:
        config = load_preset(name)
        body = config.get("format_rules", {}).get("body_text", {})
        assert body.get("font_size") is not None, f"[{name}] should define body font_size"


def test_load_preset_has_references():
    """Each preset should define reference format."""
    for name in ["ieee", "nature", "science", "apa", "chinese_thesis"]:
        config = load_preset(name)
        refs = config.get("format_rules", {}).get("references", {})
        assert refs.get("style") is not None, f"[{name}] should define reference style"


def test_load_preset_has_margins():
    """Each preset should define page margins."""
    for name in ["ieee", "nature", "science", "apa", "chinese_thesis"]:
        config = load_preset(name)
        margins = config.get("format_rules", {}).get("margins", {})
        assert margins.get("top") is not None, f"[{name}] should define top margin"
        assert margins.get("left") is not None, f"[{name}] should define left margin"


def test_load_preset_has_auto_detect():
    """Each preset should define auto_detect patterns."""
    for name in ["ieee", "nature", "science", "apa", "chinese_thesis"]:
        config = load_preset(name)
        detect = config.get("auto_detect", {})
        assert detect.get("abstract_pattern") is not None, \
            f"[{name}] should define abstract_pattern"
        assert detect.get("reference_keywords") is not None, \
            f"[{name}] should define reference_keywords"


def test_load_preset_invalid():
    """Loading a non-existent preset should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="not found"):
        load_preset("nonexistent_preset_xyz")


def test_format_preset_list():
    """format_preset_list should return a displayable string."""
    text = format_preset_list()
    assert isinstance(text, str)
    assert "ieee" in text
    assert "chinese_thesis" in text


def test_ieee_specific():
    """IEEE preset should have IEEE-specific values."""
    config = load_preset("ieee")
    body = config["format_rules"]["body_text"]
    assert body["font_size"] == 9, "IEEE body font_size should be 9pt"

    refs = config["format_rules"]["references"]
    assert refs["style"] == "IEEE"


def test_apa_specific():
    """APA preset should have APA-specific values."""
    config = load_preset("apa")
    body = config["format_rules"]["body_text"]
    assert body["font_size"] == 12, "APA body font_size should be 12pt"
    assert body["line_spacing"] == 2.0, "APA should use double spacing"

    refs = config["format_rules"]["references"]
    assert refs["style"] == "APA"


def test_chinese_thesis_specific():
    """Chinese thesis preset should match the default config values."""
    config = load_preset("chinese_thesis")
    body = config["format_rules"]["body_text"]
    assert body["font_size"] == 12, "Chinese thesis body should be 12pt (小四)"
    assert body["first_line_indent"] == 2, "Chinese thesis should indent 2 chars"

    refs = config["format_rules"]["references"]
    assert refs["style"] == "GB/T 7714"


def test_preset_apply_to_corrector(sample_paper_path, template_path, config, tmp_path):
    """Applying a preset and running correction should work end-to-end."""
    from paper_format_corrector.app import PaperFormatCorrector
    from paper_format_corrector.core.format_corrector import FormatCorrector
    from paper_format_corrector.quality.quality_scorer import QualityScorer
    from paper_format_corrector.quality.diff_reporter import DiffReporter
    from paper_format_corrector.quality.rule_engine import RuleEngine
    from paper_format_corrector.core.format_exporter import FormatExporter
    from paper_format_corrector.infra.logger import Logger

    output_path = str(tmp_path / "preset_test.docx")

    corrector = PaperFormatCorrector.__new__(PaperFormatCorrector)
    corrector.config = config
    corrector.template_path = template_path
    corrector.corrector = FormatCorrector(template_path, config)
    corrector.exporter = FormatExporter()
    corrector.scorer = QualityScorer(config)
    corrector.diff_reporter = DiffReporter()
    corrector.rule_engine = RuleEngine()
    corrector.logger = Logger(level="WARNING")

    # Apply preset
    corrector.apply_preset("ieee")

    # Verify preset was applied
    assert corrector.config["format_rules"]["body_text"]["font_size"] == 9

    # Run correction
    report = corrector.process_single(sample_paper_path, output_path)
    assert report is not None
    assert report["paragraphs_corrected"] > 0
