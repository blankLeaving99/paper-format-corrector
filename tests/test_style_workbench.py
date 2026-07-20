from docx import Document
from docx.shared import Pt

from paper_format_corrector.application.services.style_workbench import (
    build_application_report,
    explain_style_profile,
    learn_style_profile,
    manual_style_config,
    scan_document,
)


def test_scan_document_lists_elements(sample_paper_path):
    inventory = scan_document(sample_paper_path)
    assert inventory["elements"]["body"] > 0
    assert "margins" in inventory


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
