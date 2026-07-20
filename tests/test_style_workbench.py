"""Tests for style workbench services."""

from docx import Document
from docx.shared import Pt

from paper_format_corrector.application.services.style_workbench import (
    build_application_report,
    build_correction_plan,
    explain_style_profile,
    learn_style_profile,
    manual_style_config,
    plan_to_dict,
    scan_document,
)


def test_scan_document_lists_elements(sample_paper_path):
    inventory = scan_document(sample_paper_path)
    assert inventory["elements"]["body"] > 0
    assert "margins" in inventory
    assert "confidence" in inventory
    assert "page_setup" in inventory


def test_scan_document_returns_confidence(sample_paper_path):
    inventory = scan_document(sample_paper_path)
    confidence = inventory["confidence"]
    assert isinstance(confidence, list)
    for item in confidence:
        assert "element" in item
        assert "confidence" in item
        assert item["confidence"] in ("high", "medium", "low")


def test_learn_style_profile_reads_repeated_body_style(tmp_path):
    document = Document()
    for text in ("第一段正文。", "第二段正文。", "第三段正文。"):
        paragraph = document.add_paragraph(text)
        paragraph.runs[0].font.name = "SimSun"
        paragraph.runs[0].font.size = Pt(11)
    path = tmp_path / "sample.docx"
    document.save(path)

    profile = learn_style_profile(path)
    assert profile["format_rules"]["body_text"]["font_size"] == 11
    assert profile["format_rules"]["font"]["chinese"] == "SimSun"


def test_manual_style_config_exposes_table_and_image_controls():
    config = manual_style_config("宋体", 12, 1.5, 2, 16, 14, 12, "黑体", "three_line", 10.5, "80%")
    rules = config["format_rules"]
    assert rules["tables"]["style"] == "three_line"
    assert rules["images"]["max_width"] == "80%"


def test_profile_explanation_and_coverage_report(sample_paper_path):
    explanation = explain_style_profile(sample_paper_path)
    coverage = build_application_report(sample_paper_path, {"paragraphs_corrected": 1})
    assert "learned" in explanation
    assert "needs_review" in coverage


def test_build_correction_plan_identifies_elements(sample_paper_path):
    from paper_format_corrector.infra.preset_loader import load_preset
    config = load_preset("ieee")
    plan = build_correction_plan(sample_paper_path, config.get("format_rules", {}))
    assert plan.total_affected >= 0
    assert isinstance(plan.items, list)


def test_plan_to_dict_is_serializable(sample_paper_path):
    from paper_format_corrector.infra.preset_loader import load_preset
    config = load_preset("ieee")
    plan = build_correction_plan(sample_paper_path, config.get("format_rules", {}))
    d = plan_to_dict(plan)
    assert "items" in d
    assert "total_affected" in d
    assert "risk_items" in d
    # Ensure JSON serializable
    import json
    json.dumps(d)


def test_manual_style_config_all_parameters():
    config = manual_style_config(
        body_font="宋体", body_size=12, body_line_spacing=1.5, body_indent=2,
        heading1_size=16, heading2_size=14, heading3_size=12, heading_font="黑体",
        table_style="full_border", table_font_size=10.5, image_max_width="100%",
        body_en_font="Times New Roman",
        heading1_bold=True, heading2_bold=True, heading3_bold=True,
        heading1_align="center", heading2_align="left", heading3_align="left",
        abstract_size=12, abstract_indent=0,
        ref_size=10.5, ref_line_spacing=1.25,
    )
    rules = config["format_rules"]
    assert rules["font"]["chinese"] == "宋体"
    assert rules["font"]["heading_chinese"] == "黑体"
    assert rules["body_text"]["font_size"] == 12
    assert rules["headings"]["heading1"]["font_size"] == 16
    assert rules["tables"]["style"] == "full_border"
    assert rules["images"]["max_width"] == "100%"
