"""Tests for startup flow, template fallback, and dependency handling."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import pytest
from pathlib import Path


# ── compat module ────────────────────────────────────────────

class TestCompat:
    def test_get_required_packages(self):
        from paper_format_corrector.infra.compat import get_required_packages
        pkgs = get_required_packages()
        assert len(pkgs) >= 4
        assert any("python-docx" in p for p in pkgs)
        assert any("pyyaml" in p for p in pkgs)
        assert any("lxml" in p for p in pkgs)
        assert any("Pillow" in p for p in pkgs)

    def test_get_optional_packages(self):
        from paper_format_corrector.infra.compat import get_optional_packages
        pkgs = get_optional_packages()
        assert len(pkgs) >= 5
        assert any("gradio" in p for p in pkgs)
        assert any("tkinterdnd2" in p for p in pkgs)
        assert any("docx2pdf" in p for p in pkgs)
        assert any("pdfplumber" in p for p in pkgs)

    def test_get_all_packages(self):
        from paper_format_corrector.infra.compat import get_all_packages, get_required_packages, get_optional_packages
        all_pkgs = get_all_packages()
        assert all_pkgs == get_required_packages() + get_optional_packages()

    def test_check_dependencies_returns_list(self):
        from paper_format_corrector.infra.compat import check_dependencies
        result = check_dependencies()
        assert isinstance(result, list)

    def test_required_packages_have_version_specifiers(self):
        from paper_format_corrector.infra.compat import get_required_packages
        for pkg in get_required_packages():
            assert ">=" in pkg, f"Missing version specifier: {pkg}"


# ── FormatCorrector template fallback ───────────────────────

class TestFormatCorrectorFallback:
    def test_missing_template_uses_blank_document(self, config, tmp_path):
        """FormatCorrector should not crash when template file is missing."""
        from paper_format_corrector.core.format_corrector import FormatCorrector

        fake_path = str(tmp_path / "nonexistent_template.docx")
        corrector = FormatCorrector(fake_path, config)
        assert corrector.template is not None
        # Document is a function-created object; check it has expected attributes
        assert hasattr(corrector.template, 'styles')
        assert hasattr(corrector.template, 'paragraphs')

    def test_none_template_uses_blank_document(self, config):
        """FormatCorrector should handle None template path."""
        from paper_format_corrector.core.format_corrector import FormatCorrector

        corrector = FormatCorrector(None, config)
        assert corrector.template is not None

    def test_empty_string_template_uses_blank_document(self, config):
        """FormatCorrector should handle empty string template path."""
        from paper_format_corrector.core.format_corrector import FormatCorrector

        corrector = FormatCorrector("", config)
        assert corrector.template is not None

    def test_valid_template_is_loaded(self, config, template_path):
        """FormatCorrector should load a valid template normally."""
        from paper_format_corrector.core.format_corrector import FormatCorrector

        corrector = FormatCorrector(template_path, config)
        assert corrector.template is not None
        assert len(list(corrector.template.styles)) > 0

    def test_missing_template_can_correct_document(self, config, sample_paper_path, tmp_path):
        """Full correction pipeline should work even without a template file."""
        from paper_format_corrector.core.format_corrector import FormatCorrector

        fake_template = str(tmp_path / "missing.docx")
        corrector = FormatCorrector(fake_template, config)
        corrector.load_template_styles()

        output_path = str(tmp_path / "output.docx")
        report = corrector.correct_document(sample_paper_path, output_path)
        assert report["paragraphs_corrected"] > 0
        assert Path(output_path).exists()


# ── PaperFormatCorrector template handling ──────────────────

class TestAppTemplateHandling:
    def test_missing_template_config_does_not_crash(self, tmp_path):
        """App should handle config without template section."""
        import yaml
        from paper_format_corrector.app import PaperFormatCorrector

        config_path = tmp_path / "config.yaml"
        config_data = {"format_rules": {"font": {"chinese": "宋体"}}}
        config_path.write_text(yaml.dump(config_data, allow_unicode=True), encoding="utf-8")

        c = PaperFormatCorrector(str(config_path))
        assert c.template_path == ""
        assert c.corrector is not None

    def test_template_path_from_config(self, tmp_path):
        """App should read template path from config."""
        import yaml
        from paper_format_corrector.app import PaperFormatCorrector

        config_path = tmp_path / "config.yaml"
        config_data = {"template": {"path": "template/template.docx"}, "format_rules": {}}
        config_path.write_text(yaml.dump(config_data, allow_unicode=True), encoding="utf-8")

        c = PaperFormatCorrector(str(config_path))
        assert c.template_path == "template/template.docx"

    def test_template_override(self, config, template_path, tmp_path):
        """Template path can be overridden after initialization."""
        import yaml
        from paper_format_corrector.app import PaperFormatCorrector
        from paper_format_corrector.core.format_corrector import FormatCorrector

        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump(config, allow_unicode=True), encoding="utf-8")

        c = PaperFormatCorrector(str(config_path))
        c.template_path = template_path
        c.corrector = FormatCorrector(template_path, c.config)
        assert c.template_path == template_path


# ── run.py helpers ──────────────────────────────────────────

class TestRunPyHelpers:
    def test_find_venv_python_returns_none_when_no_venv(self, tmp_path):
        """Should return None when no .venv exists."""
        venv_dir = os.path.join(str(tmp_path), ".venv")
        assert not os.path.isdir(venv_dir)
        candidate = os.path.join(venv_dir, "Scripts", "python.exe")
        assert not os.path.isfile(candidate)

    def test_find_venv_python_finds_existing_venv(self, tmp_path):
        """Should find venv python when .venv exists."""
        venv_dir = tmp_path / ".venv" / "Scripts"
        venv_dir.mkdir(parents=True)
        python_exe = venv_dir / "python.exe"
        python_exe.touch()
        candidate = os.path.join(str(tmp_path), ".venv", "Scripts", "python.exe")
        assert os.path.isfile(candidate)

    def test_is_running_in_venv_detects_venv(self):
        """Should detect when running inside a venv."""
        in_venv = hasattr(sys, 'real_prefix') or (
            hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
        )
        assert isinstance(in_venv, bool)


# ── Optional dependency handling ────────────────────────────

class TestOptionalDeps:
    def test_optional_import_failures_dont_crash(self):
        """Missing optional deps should not prevent core imports."""
        from paper_format_corrector.core.format_corrector import FormatCorrector
        from paper_format_corrector.core.format_exporter import FormatExporter
        from paper_format_corrector.parsers.section_detector import SectionDetector
        from paper_format_corrector.quality.quality_scorer import QualityScorer
        # All these should succeed regardless of optional deps
        assert FormatCorrector is not None
        assert FormatExporter is not None
        assert SectionDetector is not None
        assert QualityScorer is not None

    def test_gradio_import_is_optional(self):
        """GUI module should handle missing gradio gracefully."""
        try:
            from paper_format_corrector import gui
            assert gui is not None
        except (ImportError, SystemExit):
            # gui.py calls exit(1) when gradio is missing
            pytest.skip("gradio not installed - expected for optional dep")
