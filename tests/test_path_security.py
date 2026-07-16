"""Tests for path security - Chinese path detection."""

import pytest

from paper_format_corrector.infra.path_security import (
    _CJK_RE,
    _contains_chinese,
    _validate_no_chinese,
    safe_join,
    validate_input_path,
    validate_output_path,
)


class TestCJKRegex:
    """Tests for the CJK regex pattern."""

    def test_matches_simplified_chinese(self):
        assert _CJK_RE.search("测试")

    def test_matches_traditional_chinese(self):
        assert _CJK_RE.search("測試")

    def test_matches_mixed_with_ascii(self):
        assert _CJK_RE.search("test测试test")

    def test_no_match_ascii_only(self):
        assert not _CJK_RE.search("test_file.docx")

    def test_no_match_pure_ascii_path(self):
        assert not _CJK_RE.search(r"C:\Users\Admin\file.docx")

    def test_no_match_numbers(self):
        assert not _CJK_RE.search("file123.docx")

    def test_no_match_underscores(self):
        assert not _CJK_RE.search("my_file_name.docx")

    def test_no_match_hyphens(self):
        assert not _CJK_RE.search("my-file.docx")

    def test_no_match_spaces(self):
        assert not _CJK_RE.search("my file.docx")

    def test_no_match_common_english_surnames(self):
        # Ensure common English names don't false-positive
        assert not _CJK_RE.search("Administrator")
        assert not _CJK_RE.search("Smith")
        assert not _CJK_RE.search("Johnson")


class TestContainsChinese:
    """Tests for the _contains_chinese helper."""

    def test_returns_true_for_chinese(self):
        assert _contains_chinese("论文.docx") is True

    def test_returns_false_for_ascii(self):
        assert _contains_chinese("paper.docx") is False

    def test_returns_false_for_numbers(self):
        assert _contains_chinese("12345") is False

    def test_returns_true_for_mixed(self):
        assert _contains_chinese("paper_论文.docx") is True


class TestValidateNoChinese:
    """Tests for the _validate_no_chinese validator."""

    def test_raises_for_chinese_path(self):
        with pytest.raises(ValueError, match="不允许包含中文字符"):
            _validate_no_chinese("/path/to/论文.docx")

    def test_raises_for_chinese_filename(self):
        with pytest.raises(ValueError, match="不允许包含中文字符"):
            _validate_no_chinese("我的文件.docx", label="文件名")

    def test_passes_for_ascii_path(self):
        _validate_no_chinese(r"C:\Users\Admin\paper.docx")

    def test_passes_for_empty_string(self):
        _validate_no_chinese("")


class TestSafeJoinChineseRejection:
    """Tests for safe_join rejecting Chinese filenames."""

    def test_rejects_chinese_filename(self, tmp_path):
        with pytest.raises(ValueError, match="不允许包含中文字符"):
            safe_join(str(tmp_path), "论文.docx")

    def test_accepts_ascii_filename(self, tmp_path):
        result = safe_join(str(tmp_path), "paper.docx")
        assert result.name == "paper.docx"


class TestValidateInputPathChineseRejection:
    """Tests for validate_input_path rejecting Chinese paths."""

    def test_rejects_chinese_in_path(self, tmp_path):
        # Create a file with ASCII name in a temp dir
        ascii_file = tmp_path / "paper.docx"
        ascii_file.touch()
        # Simulate a Chinese path by passing a string with Chinese chars
        with pytest.raises(ValueError, match="不允许包含中文字符"):
            validate_input_path(str(ascii_file) + "论文", {".docx"})


class TestValidateOutputPathChineseRejection:
    """Tests for validate_output_path rejecting Chinese paths."""

    def test_rejects_chinese_in_output_path(self, tmp_path):
        output = str(tmp_path / "论文_output.docx")
        with pytest.raises(ValueError, match="不允许包含中文字符"):
            validate_output_path(output, {".docx"})

    def test_accepts_ascii_output_path(self, tmp_path):
        output = str(tmp_path / "output.docx")
        result = validate_output_path(output, {".docx"})
        assert result.name == "output.docx"
