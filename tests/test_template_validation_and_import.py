"""University template import and template validation tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from paper_format_corrector.application.services.template_validation_service import (
    TemplateValidationService,
    ValidationResult,
)
from paper_format_corrector.application.services.university_template_import_service import (
    UniversityTemplateImportService,
    ImportWorkflow,
)


# ── TemplateValidationService ─────────────────────────────────


class TestTemplateValidation:
    def setup_method(self):
        self.service = TemplateValidationService()

    def test_valid_config_passes(self):
        config = {
            "format_rules": {
                "font": {"chinese": "宋体", "english": "Times New Roman"},
                "headings": {
                    "heading1": {"font_size": 16, "bold": True, "align": "center"},
                    "heading2": {"font_size": 14, "bold": True, "align": "left"},
                    "heading3": {"font_size": 12, "bold": True, "align": "left"},
                },
                "body_text": {"font_size": 12, "line_spacing": 1.5},
                "margins": {"top": 3.0, "bottom": 3.0, "left": 2.5, "right": 2.5},
                "abstract": {"title_font_size": 14, "title_bold": True},
            }
        }
        result = self.service.validate_config(config)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_missing_format_rules_fails(self):
        result = self.service.validate_config({})
        assert result.is_valid is False
        assert any("format_rules" in e for e in result.errors)

    def test_missing_font_section_fails(self):
        config = {
            "format_rules": {
                "headings": {
                    "heading1": {"font_size": 16, "bold": True, "align": "center"},
                    "heading2": {"font_size": 14, "bold": True, "align": "left"},
                    "heading3": {"font_size": 12, "bold": True, "align": "left"},
                },
                "body_text": {"font_size": 12, "line_spacing": 1.5},
                "margins": {"top": 3.0, "bottom": 3.0, "left": 2.5, "right": 2.5},
                "abstract": {"title_font_size": 14, "title_bold": True},
            }
        }
        result = self.service.validate_config(config)
        assert result.is_valid is False
        assert any("font" in e for e in result.errors)

    def test_missing_heading_levels_fails(self):
        config = {
            "format_rules": {
                "font": {"chinese": "宋体", "english": "Times New Roman"},
                "headings": {"heading1": {"font_size": 16, "bold": True, "align": "center"}},
                "body_text": {"font_size": 12, "line_spacing": 1.5},
                "margins": {"top": 3.0, "bottom": 3.0, "left": 2.5, "right": 2.5},
                "abstract": {"title_font_size": 14, "title_bold": True},
            }
        }
        result = self.service.validate_config(config)
        assert any("heading2" in e for e in result.errors)

    def test_suggests_optional_sections(self):
        config = {
            "format_rules": {
                "font": {"chinese": "宋体", "english": "Times New Roman"},
                "headings": {
                    "heading1": {"font_size": 16, "bold": True, "align": "center"},
                    "heading2": {"font_size": 14, "bold": True, "align": "left"},
                    "heading3": {"font_size": 12, "bold": True, "align": "left"},
                },
                "body_text": {"font_size": 12, "line_spacing": 1.5},
                "margins": {"top": 3.0, "bottom": 3.0, "left": 2.5, "right": 2.5},
                "abstract": {"title_font_size": 14, "title_bold": True},
            }
        }
        result = self.service.validate_config(config)
        assert len(result.suggestions) > 0

    def test_generate_report(self):
        result = ValidationResult(is_valid=True, warnings=["test warning"])
        report = self.service.generate_report(result)
        assert "验证通过" in report
        assert "test warning" in report


# ── UniversityTemplateImportService ───────────────────────────


class TestUniversityTemplateImport:
    def test_create_workflow(self):
        service = UniversityTemplateImportService()
        workflow = service.create_workflow("清华大学", "test_req.docx")
        assert workflow.university == "清华大学"
        assert workflow.requirement_file == "test_req.docx"
        assert len(workflow.steps) == 4

    def test_get_workflow_status(self):
        service = UniversityTemplateImportService()
        workflow = service.create_workflow("北京大学", "test.docx")
        status = service.get_workflow_status(workflow)
        assert status["university"] == "北京大学"
        assert status["progress"] == "0/4"
        assert status["is_complete"] is False

    def test_generate_slug(self):
        service = UniversityTemplateImportService()
        slug = service._generate_slug("清华大学")
        assert isinstance(slug, str)
        assert len(slug) > 0

    def test_workflow_steps_names(self):
        service = UniversityTemplateImportService()
        workflow = service.create_workflow("测试大学", "test.docx")
        step_names = [s.name for s in workflow.steps]
        assert "parse_requirement" in step_names
        assert "generate_config" in step_names
        assert "validate_config" in step_names
        assert "save_template" in step_names

    def test_workflow_initial_state(self):
        service = UniversityTemplateImportService()
        workflow = service.create_workflow("测试", "test.docx")
        for step in workflow.steps:
            assert step.status == "pending"
        assert workflow.is_complete is False
        assert workflow.error == ""

    def test_execute_workflow_with_nonexistent_file(self):
        service = UniversityTemplateImportService()
        workflow = service.create_workflow("测试", "nonexistent_file_12345.docx")
        workflow = service.execute_workflow(workflow)
        assert workflow.error != "" or workflow.steps[0].status == "failed"
