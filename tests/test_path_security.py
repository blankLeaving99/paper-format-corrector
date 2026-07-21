"""Tests for path security - safe path validation."""

import pytest

from paper_format_corrector.infrastructure.path_security import (
    _DANGEROUS_CHARS_RE,
    _is_safe_path,
    _validate_path_safety,
    safe_join,
    validate_input_path,
    validate_output_path,
)


class TestDangerousCharsRegex:
    """Tests for the dangerous characters regex pattern."""

    def test_rejects_control_chars(self):
        assert _DANGEROUS_CHARS_RE.search("\x00test")
        assert _DANGEROUS_CHARS_RE.search("\x1ftest")

    def test_rejects_angle_brackets(self):
        assert _DANGEROUS_CHARS_RE.search("test<file")
        assert _DANGEROUS_CHARS_RE.search("test>file")

    def test_rejects_quote(self):
        assert _DANGEROUS_CHARS_RE.search('test"file')

    def test_rejects_pipe(self):
        assert _DANGEROUS_CHARS_RE.search("test|file")

    def test_rejects_question_mark(self):
        assert _DANGEROUS_CHARS_RE.search("test?file")

    def test_rejects_asterisk(self):
        assert _DANGEROUS_CHARS_RE.search("test*file")

    def test_no_match_ascii_only(self):
        assert not _DANGEROUS_CHARS_RE.search("test_file.docx")

    def test_no_match_chinese(self):
        assert not _DANGEROUS_CHARS_RE.search("论文.docx")

    def test_no_match_mixed_ascii_chinese(self):
        assert not _DANGEROUS_CHARS_RE.search("paper_论文.docx")

    def test_no_match_numbers(self):
        assert not _DANGEROUS_CHARS_RE.search("file123.docx")


class TestIsSafePath:
    """Tests for the _is_safe_path helper."""

    def test_returns_true_for_ascii(self):
        assert _is_safe_path("paper.docx") is True

    def test_returns_true_for_chinese(self):
        assert _is_safe_path("论文.docx") is True

    def test_returns_true_for_mixed(self):
        assert _is_safe_path("paper_论文.docx") is True

    def test_returns_false_for_dangerous_chars(self):
        assert _is_safe_path("test<file>.docx") is False

    def test_returns_true_for_empty_string(self):
        assert _is_safe_path("") is True


class TestValidatePathSafety:
    """Tests for the _validate_path_safety validator."""

    def test_raises_for_dangerous_chars(self):
        with pytest.raises(ValueError, match="包含不允许的字符"):
            _validate_path_safety("/path/to/test<file>.docx")

    def test_passes_for_chinese_path(self):
        _validate_path_safety("/path/to/论文.docx")

    def test_passes_for_ascii_path(self):
        _validate_path_safety(r"C:\Users\Admin\paper.docx")

    def test_passes_for_empty_string(self):
        _validate_path_safety("")


class TestSafeJoin:
    """Tests for safe_join function."""

    def test_rejects_path_separators(self, tmp_path):
        with pytest.raises(ValueError, match="路径分隔符"):
            safe_join(str(tmp_path), "sub/paper.docx")

    def test_rejects_dotdot(self, tmp_path):
        with pytest.raises(ValueError):
            safe_join(str(tmp_path), "../paper.docx")

    def test_accepts_chinese_filename(self, tmp_path):
        result = safe_join(str(tmp_path), "论文.docx")
        assert result.name == "论文.docx"

    def test_accepts_ascii_filename(self, tmp_path):
        result = safe_join(str(tmp_path), "paper.docx")
        assert result.name == "paper.docx"


class TestValidateInputPath:
    """Tests for validate_input_path."""

    def test_rejects_dangerous_chars(self, tmp_path):
        file = tmp_path / "test.docx"
        file.touch()
        with pytest.raises(ValueError, match="包含不允许的字符"):
            validate_input_path(str(file) + "<invalid>", {".docx"})

    def test_accepts_chinese_path(self, tmp_path):
        file = tmp_path / "论文.docx"
        file.touch()
        result = validate_input_path(str(file), {".docx"})
        assert result.name == "论文.docx"


class TestValidateOutputPath:
    """Tests for validate_output_path."""

    def test_rejects_dangerous_chars(self, tmp_path):
        output = str(tmp_path / "test<invalid>.docx")
        with pytest.raises(ValueError, match="包含不允许的字符"):
            validate_output_path(output, {".docx"})

    def test_accepts_chinese_path(self, tmp_path):
        output = str(tmp_path / "论文_output.docx")
        result = validate_output_path(output, {".docx"})
        assert result.name == "论文_output.docx"

    def test_accepts_ascii_path(self, tmp_path):
        output = str(tmp_path / "output.docx")
        result = validate_output_path(output, {".docx"})
        assert result.name == "output.docx"
