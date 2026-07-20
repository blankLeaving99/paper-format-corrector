"""Tests for report service including history storage."""

import json

from paper_format_corrector.application.services.report_service import (
    ReportData,
    ReportService,
    report_from_correction,
)


def test_report_service_generates_html():
    svc = ReportService()
    data = ReportData(
        input_file="test.docx",
        output_file="output.docx",
        total_elements=100,
        modified_elements=80,
        applied={"body": 50, "headings": 20, "tables": 10},
    )
    html = svc.generate_html(data)
    assert "论文格式矫正报告" in html
    assert "test.docx" in html
    assert "80" in html


def test_report_service_generates_markdown():
    svc = ReportService()
    data = ReportData(
        input_file="test.docx",
        output_file="output.docx",
        total_elements=100,
        modified_elements=80,
    )
    md = svc.generate_markdown(data)
    assert "# 论文格式矫正报告" in md
    assert "test.docx" in md


def test_report_service_generates_json():
    svc = ReportService()
    data = ReportData(
        input_file="test.docx",
        output_file="output.docx",
        total_elements=100,
        modified_elements=80,
        citation_issues=[{"type": "missing_in_text", "message": "test issue"}],
    )
    j = svc.generate_json(data)
    parsed = json.loads(j)
    assert "meta" in parsed
    assert "summary" in parsed
    assert "citation_issues" in parsed
    assert len(parsed["citation_issues"]) == 1


def test_report_service_saves_and_loads_history(tmp_path):
    svc = ReportService()
    db_path = tmp_path / "history.db"
    data = ReportData(
        input_file="test.docx",
        output_file="output.docx",
        template_used="ieee",
        quality_score=90.0,
        total_elements=100,
        modified_elements=85,
        processing_time=3.2,
        applied={"body": 60, "headings": 25},
    )
    record_id = svc.save_history(data, database_path=db_path)
    assert record_id > 0

    # Verify via repository
    from paper_format_corrector.infra.template_repository import TemplateRepository
    repo = TemplateRepository(db_path)
    history = repo.list_processing_history()
    assert len(history) >= 1
    assert history[0]["quality_score"] == 90.0


def test_report_from_correction_converts_dict():
    correction_report = {
        "paragraphs_corrected": 50,
        "headings_fixed": 10,
        "body_fixed": 30,
        "tables_formatted": 5,
        "images_centered": 8,
        "warnings": ["test warning"],
        "citation_issues": [{"type": "duplicate", "message": "dup"}],
    }
    data = report_from_correction(correction_report, "input.docx", "output.docx")
    assert data.input_file == "input.docx"
    assert data.applied["paragraphs"] == 50
    assert data.citation_issues is not None
    assert len(data.citation_issues) == 1


def test_report_service_html_includes_citation_issues():
    svc = ReportService()
    data = ReportData(
        input_file="test.docx",
        output_file="output.docx",
        citation_issues=[
            {"type": "missing_in_references", "message": "正文引用 [3] 在参考文献中未找到"},
            {"type": "missing_in_text", "message": "参考文献条目 [5] 未被正文引用"},
        ],
    )
    html = svc.generate_html(data)
    assert "引用一致性检查" in html
    assert "正文引用 [3]" in html
