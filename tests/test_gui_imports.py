"""GUI import and function tests.

Tests that GUI modules can be imported and key functions exist.
Does NOT require a display — tests function signatures and logic only.
"""

from __future__ import annotations

import inspect
import sys
from unittest.mock import MagicMock, patch

import pytest


# ── Web GUI (Gradio) ──────────────────────────────────────────


class TestWebGUIImports:
    """Verify gui.py imports and key functions exist."""

    def test_gui_module_has_gradio_guard(self):
        """gui.py should have gradio import guard."""
        from pathlib import Path
        gui_path = Path("src/paper_format_corrector/interfaces/web/app.py")
        content = gui_path.read_text(encoding="utf-8")
        assert "import gradio" in content
        assert "ModuleNotFoundError" in content or "pip install gradio" in content

    def test_gui_module_process_batch_files_defined(self):
        """process_batch_files function should be defined in gui.py."""
        from pathlib import Path
        gui_path = Path("src/paper_format_corrector/interfaces/web/app.py")
        content = gui_path.read_text(encoding="utf-8")
        assert "def process_batch_files(" in content

    def test_gui_module_refresh_override_table_defined(self):
        from pathlib import Path
        gui_path = Path("src/paper_format_corrector/interfaces/web/app.py")
        content = gui_path.read_text(encoding="utf-8")
        assert "def refresh_override_table(" in content

    def test_gui_module_preview_correction_plan_defined(self):
        from pathlib import Path
        gui_path = Path("src/paper_format_corrector/interfaces/web/app.py")
        content = gui_path.read_text(encoding="utf-8")
        assert "def preview_correction_plan(" in content

    def test_gui_module_inspect_sample_style_defined(self):
        from pathlib import Path
        gui_path = Path("src/paper_format_corrector/interfaces/web/app.py")
        content = gui_path.read_text(encoding="utf-8")
        assert "def inspect_sample_style(" in content

    def test_gui_module_save_sample_template_defined(self):
        from pathlib import Path
        gui_path = Path("src/paper_format_corrector/interfaces/web/app.py")
        content = gui_path.read_text(encoding="utf-8")
        assert "def save_sample_template(" in content

    def test_gui_module_generate_cover_defined(self):
        from pathlib import Path
        gui_path = Path("src/paper_format_corrector/interfaces/web/app.py")
        content = gui_path.read_text(encoding="utf-8")
        assert "def generate_cover(" in content

    def test_gui_module_process_with_workbench_defined(self):
        from pathlib import Path
        gui_path = Path("src/paper_format_corrector/interfaces/web/app.py")
        content = gui_path.read_text(encoding="utf-8")
        assert "def process_with_workbench(" in content

    def test_gui_has_template_management_tab(self):
        from pathlib import Path
        gui_path = Path("src/paper_format_corrector/interfaces/web/app.py")
        content = gui_path.read_text(encoding="utf-8")
        assert "模板库管理" in content or "模板管理" in content

    def test_gui_has_batch_tab(self):
        from pathlib import Path
        gui_path = Path("src/paper_format_corrector/interfaces/web/app.py")
        content = gui_path.read_text(encoding="utf-8")
        assert "批量处理" in content

    def test_gui_has_report_center_tab(self):
        from pathlib import Path
        gui_path = Path("src/paper_format_corrector/interfaces/web/app.py")
        content = gui_path.read_text(encoding="utf-8")
        assert "报告中心" in content


# ── Desktop GUI (tkinter) ─────────────────────────────────────


class TestDesktopGUIImports:
    """Verify desktop_gui.py imports and key class exists."""

    def test_desktop_gui_module_exists(self):
        from pathlib import Path
        gui_path = Path("src/paper_format_corrector/interfaces/desktop/app.py")
        assert gui_path.exists()

    def test_desktop_gui_has_main_class(self):
        from pathlib import Path
        gui_path = Path("src/paper_format_corrector/interfaces/desktop/app.py")
        content = gui_path.read_text(encoding="utf-8")
        assert "class PaperFormatDesktopApp" in content

    def test_desktop_gui_has_key_methods(self):
        from pathlib import Path
        gui_path = Path("src/paper_format_corrector/interfaces/desktop/app.py")
        content = gui_path.read_text(encoding="utf-8")
        key_methods = [
            "_run_batch_correct",
            "_process_single",
            "_show_result",
            "_set_buttons_state",
        ]
        for method in key_methods:
            assert method in content, f"Missing method: {method}"

    def test_desktop_gui_has_template_tab(self):
        from pathlib import Path
        gui_path = Path("src/paper_format_corrector/interfaces/desktop/app.py")
        content = gui_path.read_text(encoding="utf-8")
        assert "模板管理" in content or "_build_template_tab" in content

    def test_desktop_gui_has_confidence_list(self):
        from pathlib import Path
        gui_path = Path("src/paper_format_corrector/interfaces/desktop/app.py")
        content = gui_path.read_text(encoding="utf-8")
        assert "_refresh_confidence_list" in content or "confidence" in content.lower()

    def test_desktop_gui_has_batch_processing(self):
        from pathlib import Path
        gui_path = Path("src/paper_format_corrector/interfaces/desktop/app.py")
        content = gui_path.read_text(encoding="utf-8")
        assert "批量处理" in content

    def test_desktop_gui_imports_safely(self):
        """desktop_gui should import without display."""
        import paper_format_corrector.interfaces.desktop.app as gui_mod
        assert gui_mod is not None


# ── Application Services ──────────────────────────────────────


class TestApplicationServiceImports:
    """Verify all application services can be imported."""

    def test_import_batch_service(self):
        from paper_format_corrector.application.batch_service import (
            BatchCorrectionService,
            BatchSummary,
        )
        assert callable(BatchCorrectionService)
        assert callable(BatchSummary)

    def test_import_report_service(self):
        from paper_format_corrector.application.report_service import (
            ReportService,
            ReportData,
        )
        assert callable(ReportService)
        assert callable(ReportData)

    def test_import_template_validation_service(self):
        from paper_format_corrector.application.template_validation_service import (
            TemplateValidationService,
            ValidationResult,
        )
        assert callable(TemplateValidationService)
        assert callable(ValidationResult)

    def test_import_style_workbench(self):
        from paper_format_corrector.application import style_workbench
        assert hasattr(style_workbench, "CorrectionPlan") or hasattr(style_workbench, "CorrectionPlanItem")

    def test_import_university_template_import_service(self):
        from paper_format_corrector.application.university_template_import_service import (
            UniversityTemplateImportService,
        )
        assert callable(UniversityTemplateImportService)

    def test_batch_summary_has_create_zip(self):
        from paper_format_corrector.application.batch_service import BatchSummary
        assert hasattr(BatchSummary, "create_zip")

    def test_batch_summary_has_generate_report(self):
        from paper_format_corrector.application.batch_service import BatchSummary
        assert hasattr(BatchSummary, "generate_report")

    def test_report_service_has_pdf_export(self):
        from paper_format_corrector.application.report_service import ReportService
        rs = ReportService()
        assert hasattr(rs, "_save_pdf_with_fallback")


# ── Core Modules ──────────────────────────────────────────────


class TestCoreModuleImports:
    """Verify core modules can be imported."""

    def test_import_format_corrector(self):
        from paper_format_corrector.domain.correction.engine import FormatCorrector
        assert callable(FormatCorrector)

    def test_import_format_exporter(self):
        from paper_format_corrector.infrastructure.exporters.format_exporter import FormatExporter
        assert callable(FormatExporter)

    def test_import_style_extractor(self):
        from paper_format_corrector.domain.correction.extractor import StyleExtractor
        assert callable(StyleExtractor)

    def test_import_table_handler(self):
        from paper_format_corrector.domain.document.elements.table_handler import TableHandler
        assert callable(TableHandler)

    def test_import_image_handler(self):
        from paper_format_corrector.domain.document.elements.image_handler import ImageHandler
        assert callable(ImageHandler)

    def test_import_section_detector(self):
        from paper_format_corrector.domain.document.parser.structure import SectionDetector
        assert callable(SectionDetector)

    def test_import_reference_formatter(self):
        from paper_format_corrector.domain.document.parser.reference import ReferenceFormatter
        assert callable(ReferenceFormatter)

    def test_import_cross_reference(self):
        from paper_format_corrector.domain.document.cross_reference import CrossReferenceUpdater
        assert callable(CrossReferenceUpdater)

    def test_import_diff_reporter(self):
        from paper_format_corrector.domain.quality.diff_reporter import DiffReporter
        assert callable(DiffReporter)

    def test_import_quality_scorer(self):
        from paper_format_corrector.domain.quality.quality_scorer import QualityScorer
        assert callable(QualityScorer)

    def test_import_cover_page_generator(self):
        from paper_format_corrector.infrastructure.generators.cover_generator import CoverPageGenerator
        assert callable(CoverPageGenerator)

    def test_import_file_converter(self):
        from paper_format_corrector.infrastructure.converters.file_converter import FileConverter
        assert callable(FileConverter)

    def test_image_handler_has_dpi_check(self):
        from paper_format_corrector.domain.document.elements.image_handler import ImageHandler
        assert hasattr(ImageHandler, "_check_dpi") or hasattr(ImageHandler, "check_pixel_dpi")

    def test_format_corrector_has_renumber_formulas(self):
        from paper_format_corrector.infrastructure.converters.file_formatter import FormatCorrector
        assert hasattr(FormatCorrector, "_renumber_formulas")


# ── Infrastructure ────────────────────────────────────────────


class TestInfrastructureImports:
    """Verify infrastructure modules can be imported."""

    def test_import_template_repository(self):
        from paper_format_corrector.infrastructure.template_repository import TemplateRepository
        assert callable(TemplateRepository)

    def test_import_preset_loader(self):
        from paper_format_corrector.infrastructure.preset_loader import load_preset, list_presets
        assert callable(load_preset)
        assert callable(list_presets)

    def test_import_path_security(self):
        from paper_format_corrector.infrastructure.path_security import validate_input_path, validate_output_path
        assert callable(validate_input_path)
        assert callable(validate_output_path)

    def test_import_compatibility(self):
        from paper_format_corrector.infrastructure.compat import check_dependencies
        assert callable(check_dependencies)

    def test_list_presets_returns_multiple(self):
        from paper_format_corrector.infrastructure.preset_loader import list_presets
        presets = list_presets()
        assert len(presets) >= 20
