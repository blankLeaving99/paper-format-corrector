"""Tests for PDF style extractor (OCR/PDF reverse learning)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from paper_format_corrector.core.document.pdf_style_extractor import (
    PDFTextBlock,
    PDFPageInfo,
    _classify_block,
    _dominant_body_rule,
    _dominant_heading_rule,
    _infer_font_names,
    _group_chars_into_blocks,
    extract_pdf_style,
)


# ---------------------------------------------------------------------------
# PDFTextBlock classification
# ---------------------------------------------------------------------------

class TestClassifyBlock:
    """Test paragraph type classification from PDF text blocks."""

    def _make_block(self, text, font_size=12, is_bold=False, x=0, page_width=595):
        return PDFTextBlock(
            text=text, font_name="SimSun", font_size=font_size,
            is_bold=is_bold, is_italic=False,
            x=x, y=100, width=400, height=14,
            page_width=page_width, page_height=842,
            page_num=0,
        )

    def test_heading1_chapter(self):
        block = self._make_block("第一章 绪论", font_size=16, is_bold=True)
        assert _classify_block(block) == "heading1"

    def test_heading1_numbered(self):
        block = self._make_block("1 引言", font_size=16, is_bold=True)
        assert _classify_block(block) == "heading1"

    def test_heading2(self):
        block = self._make_block("1.1 研究背景", font_size=14, is_bold=True)
        assert _classify_block(block) == "heading2"

    def test_heading3(self):
        block = self._make_block("1.1.1 国内研究", font_size=12, is_bold=True)
        assert _classify_block(block) == "heading3"

    def test_abstract_title(self):
        block = self._make_block("摘  要", font_size=16, is_bold=True)
        assert _classify_block(block) == "abstract_title"

    def test_abstract_english(self):
        block = self._make_block("Abstract", font_size=14, is_bold=True)
        assert _classify_block(block) == "abstract_title"

    def test_keywords_cn(self):
        block = self._make_block("关键词：深度学习；目标检测", font_size=10.5)
        assert _classify_block(block) == "keywords"

    def test_keywords_en(self):
        block = self._make_block("Keywords: deep learning", font_size=10.5)
        assert _classify_block(block) == "keywords"

    def test_references_title(self):
        block = self._make_block("参考文献", font_size=14, is_bold=True)
        assert _classify_block(block) == "reference"

    def test_reference_entry(self):
        block = self._make_block("[1] Zhang Y. Deep learning. Nature, 2020.", font_size=10)
        assert _classify_block(block) == "reference"

    def test_figure_caption(self):
        block = self._make_block("图 1 网络结构示意图", font_size=9)
        assert _classify_block(block) == "figure_caption"

    def test_figure_caption_english(self):
        block = self._make_block("Figure 2. Network architecture.", font_size=9)
        assert _classify_block(block) == "figure_caption"

    def test_table_caption(self):
        block = self._make_block("表 1 实验结果对比", font_size=9)
        assert _classify_block(block) == "table_caption"

    def test_table_caption_english(self):
        block = self._make_block("Table 3 Comparison of results.", font_size=9)
        assert _classify_block(block) == "table_caption"

    def test_body_text(self):
        block = self._make_block("这是一段正文内容，用于测试分类器。", font_size=12)
        assert _classify_block(block) == "body"

    def test_bold_short_as_heading(self):
        block = self._make_block("实验方法", font_size=13, is_bold=True)
        assert _classify_block(block) == "heading2"


# ---------------------------------------------------------------------------
# Dominant rule extraction
# ---------------------------------------------------------------------------

class TestDominantBodyRule:
    """Test finding dominant body text formatting."""

    def test_returns_none_for_empty(self):
        assert _dominant_body_rule([]) is None

    def test_single_block(self):
        blocks = [PDFTextBlock(
            text="test", font_name="SimSun", font_size=12,
            is_bold=False, is_italic=False,
            x=100, y=100, width=400, height=14,
            page_width=595, page_height=842, page_num=0,
        )]
        rule = _dominant_body_rule(blocks)
        assert rule is not None
        assert rule["font_size"] == 12
        assert rule["bold"] is False

    def test_consistent_blocks(self):
        blocks = [
            PDFTextBlock(text=f"line {i}", font_name="SimSun", font_size=12,
                        is_bold=False, is_italic=False,
                        x=100, y=100 + i * 20, width=400, height=14,
                        page_width=595, page_height=842, page_num=0)
            for i in range(5)
        ]
        rule = _dominant_body_rule(blocks)
        assert rule is not None
        assert rule["font_size"] == 12


class TestDominantHeadingRule:
    """Test finding dominant heading formatting."""

    def test_returns_none_for_empty(self):
        assert _dominant_heading_rule([]) is None

    def test_bold_heading(self):
        blocks = [PDFTextBlock(
            text="Chapter 1", font_name="SimHei", font_size=16,
            is_bold=True, is_italic=False,
            x=50, y=100, width=200, height=20,
            page_width=595, page_height=842, page_num=0,
        )]
        rule = _dominant_heading_rule(blocks)
        assert rule is not None
        assert rule["font_size"] == 16
        assert rule["bold"] is True


# ---------------------------------------------------------------------------
# Font name inference
# ---------------------------------------------------------------------------

class TestInferFontNames:
    """Test Chinese/English font name inference."""

    def test_returns_defaults_for_unknown(self):
        blocks = [PDFTextBlock(
            text="test", font_name="unknown", font_size=12,
            is_bold=False, is_italic=False,
            x=0, y=0, width=100, height=14,
            page_width=595, page_height=842, page_num=0,
        )]
        result = _infer_font_names(blocks)
        assert result["chinese"] == "宋体"
        assert result["english"] == "Times New Roman"

    def test_detects_simsun(self):
        blocks = [PDFTextBlock(
            text="test", font_name="SimSun", font_size=12,
            is_bold=False, is_italic=False,
            x=0, y=0, width=100, height=14,
            page_width=595, page_height=842, page_num=0,
        )]
        result = _infer_font_names(blocks)
        assert result["chinese"] == "SimSun"

    def test_detects_times_new_roman(self):
        blocks = [PDFTextBlock(
            text="test", font_name="TimesNewRoman", font_size=12,
            is_bold=False, is_italic=False,
            x=0, y=0, width=100, height=14,
            page_width=595, page_height=842, page_num=0,
        )]
        result = _infer_font_names(blocks)
        assert result["english"] == "TimesNewRoman"


# ---------------------------------------------------------------------------
# Char grouping
# ---------------------------------------------------------------------------

class TestGroupCharsIntoBlocks:
    """Test pdfplumber char-to-block grouping."""

    def test_empty_chars(self):
        assert _group_chars_into_blocks([], 595, 842, 0) == []

    def test_single_line(self):
        chars = [
            {"text": "H", "fontname": "SimSun", "size": 12, "x0": 100, "x1": 110, "top": 100, "bottom": 114},
            {"text": "i", "fontname": "SimSun", "size": 12, "x0": 112, "x1": 118, "top": 100, "bottom": 114},
        ]
        blocks = _group_chars_into_blocks(chars, 595, 842, 0)
        assert len(blocks) == 1
        assert blocks[0].text == "Hi"

    def test_two_lines(self):
        chars = [
            {"text": "A", "fontname": "SimSun", "size": 12, "x0": 100, "x1": 110, "top": 100, "bottom": 114},
            {"text": "B", "fontname": "SimSun", "size": 12, "x0": 100, "x1": 110, "top": 120, "bottom": 134},
        ]
        blocks = _group_chars_into_blocks(chars, 595, 842, 0)
        assert len(blocks) == 2


# ---------------------------------------------------------------------------
# extract_pdf_style with mock
# ---------------------------------------------------------------------------

class TestExtractPdfStyle:
    """Test the main extract_pdf_style function."""

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            extract_pdf_style("/nonexistent/file.pdf")

    def test_not_pdf(self, tmp_path):
        txt = tmp_path / "test.txt"
        txt.write_text("hello")
        with pytest.raises(ValueError, match="不是 PDF 文件"):
            extract_pdf_style(txt)

    @patch("paper_format_corrector.core.document.pdf_style_extractor._extract_with_pdfplumber")
    def test_returns_config_from_pdfplumber(self, mock_extract, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")

        block = PDFTextBlock(
            text="第一章 绪论", font_name="SimHei", font_size=16,
            is_bold=True, is_italic=False,
            x=50, y=100, width=200, height=20,
            page_width=595, page_height=842, page_num=0,
        )
        body_block = PDFTextBlock(
            text="这是正文内容，用于测试样式提取功能。", font_name="SimSun", font_size=12,
            is_bold=False, is_italic=False,
            x=100, y=150, width=400, height=14,
            page_width=595, page_height=842, page_num=0,
        )

        page = PDFPageInfo(page_num=0, width=595, height=842, text_blocks=[block, body_block])
        mock_extract.return_value = [page]

        config = extract_pdf_style(pdf)
        assert "format_rules" in config
        rules = config["format_rules"]
        assert "body_text" in rules
        assert "headings" in rules
        assert "_extraction" in rules

    @patch("paper_format_corrector.core.document.pdf_style_extractor._extract_with_pdfplumber")
    def test_no_blocks_raises(self, mock_extract, tmp_path):
        pdf = tmp_path / "empty.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")
        page = PDFPageInfo(page_num=0, width=595, height=842, text_blocks=[])
        mock_extract.return_value = [page]

        with pytest.raises(RuntimeError, match="未提取到文本"):
            extract_pdf_style(pdf)
