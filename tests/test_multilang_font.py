"""多语言字体测试

测试 _get_script_type()、_apply_mixed_font()、_set_run_font() 对中文/日文/韩文/英文的正确处理。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest
from docx import Document

from paper_format_corrector.infrastructure.converters.file_formatter import FormatCorrector


class TestGetScriptType:
    """测试 _get_script_type() 静态方法"""

    def test_chinese_characters(self):
        assert FormatCorrector._get_script_type("你") == "zh"
        assert FormatCorrector._get_script_type("世") == "zh"
        assert FormatCorrector._get_script_type("界") == "zh"

    def test_japanese_hiragana(self):
        assert FormatCorrector._get_script_type("あ") == "ja"
        assert FormatCorrector._get_script_type("ん") == "ja"
        assert FormatCorrector._get_script_type("は") == "ja"

    def test_japanese_katakana(self):
        assert FormatCorrector._get_script_type("ア") == "ja"
        assert FormatCorrector._get_script_type("ン") == "ja"
        assert FormatCorrector._get_script_type("カ") == "ja"

    def test_korean_hangul(self):
        assert FormatCorrector._get_script_type("가") == "ko"
        assert FormatCorrector._get_script_type("힣") == "ko"
        assert FormatCorrector._get_script_type("한") == "ko"

    def test_english_characters(self):
        assert FormatCorrector._get_script_type("A") == "en"
        assert FormatCorrector._get_script_type("z") == "en"
        assert FormatCorrector._get_script_type("H") == "en"

    def test_other_characters(self):
        assert FormatCorrector._get_script_type("1") == "other"
        assert FormatCorrector._get_script_type(" ") == "other"
        assert FormatCorrector._get_script_type(".") == "other"


class TestApplyMixedFont:
    """测试 _apply_mixed_font() 多语言字体应用"""

    @pytest.fixture
    def corrector(self):
        config = {
            "format_rules": {
                "font": {
                    "chinese": "宋体",
                    "japanese": "MS Mincho",
                    "korean": "Batang",
                    "english": "Times New Roman",
                }
            }
        }
        return FormatCorrector(template_path=None, config=config)

    def test_japanese_run_uses_japanese_font(self, corrector):
        doc = Document()
        para = doc.add_paragraph()
        run = para.add_run("こんにちは")
        font_rules = {
            "chinese": "宋体",
            "japanese": "MS Mincho",
            "korean": "Batang",
            "english": "Times New Roman",
        }
        style_rules = {"font_size": 12}
        corrector._apply_mixed_font(para, font_rules, style_rules)
        assert run.font.name == "MS Mincho"

    def test_korean_run_uses_korean_font(self, corrector):
        doc = Document()
        para = doc.add_paragraph()
        run = para.add_run("안녕하세요")
        font_rules = {
            "chinese": "宋体",
            "japanese": "MS Mincho",
            "korean": "Batang",
            "english": "Times New Roman",
        }
        style_rules = {"font_size": 12}
        corrector._apply_mixed_font(para, font_rules, style_rules)
        assert run.font.name == "Batang"

    def test_chinese_run_uses_chinese_font(self, corrector):
        doc = Document()
        para = doc.add_paragraph()
        run = para.add_run("你好世界")
        font_rules = {
            "chinese": "宋体",
            "japanese": "MS Mincho",
            "korean": "Batang",
            "english": "Times New Roman",
        }
        style_rules = {"font_size": 12}
        corrector._apply_mixed_font(para, font_rules, style_rules)
        assert run.font.name == "宋体"

    def test_english_run_uses_english_font(self, corrector):
        doc = Document()
        para = doc.add_paragraph()
        run = para.add_run("Hello World")
        font_rules = {
            "chinese": "宋体",
            "japanese": "MS Mincho",
            "korean": "Batang",
            "english": "Times New Roman",
        }
        style_rules = {"font_size": 12}
        corrector._apply_mixed_font(para, font_rules, style_rules)
        assert run.font.name == "Times New Roman"

    def test_mixed_chinese_english_uses_dominant(self, corrector):
        doc = Document()
        para = doc.add_paragraph()
        # 中文为主，英文为辅
        run = para.add_run("这是一个测试test")
        font_rules = {
            "chinese": "宋体",
            "japanese": "MS Mincho",
            "korean": "Batang",
            "english": "Times New Roman",
        }
        style_rules = {"font_size": 12}
        corrector._apply_mixed_font(para, font_rules, style_rules)
        # 中文字符多于英文，应使用中文字体
        assert run.font.name == "宋体"


class TestSetRunFont:
    """测试 _set_run_font() 语言感知字体选择"""

    def test_chinese_language_uses_chinese_font(self):
        config = {"format_rules": {"font": {}}}
        corrector = FormatCorrector(template_path=None, config=config)
        corrector._detected_language = "chinese"

        doc = Document()
        para = doc.add_paragraph()
        run = para.add_run("测试")
        font_rules = {"chinese": "宋体", "english": "Times New Roman"}
        style_rules = {}

        corrector._set_run_font(run, font_rules, style_rules)
        assert run.font.name == "Times New Roman"

    def test_japanese_language_uses_japanese_font(self):
        config = {"format_rules": {"font": {}}}
        corrector = FormatCorrector(template_path=None, config=config)
        corrector._detected_language = "japanese"

        doc = Document()
        para = doc.add_paragraph()
        run = para.add_run("テスト")
        font_rules = {
            "chinese": "宋体",
            "japanese": "MS Mincho",
            "english": "Times New Roman",
        }
        style_rules = {}

        corrector._set_run_font(run, font_rules, style_rules)
        assert run.font.name == "Times New Roman"

    def test_korean_language_uses_korean_font(self):
        config = {"format_rules": {"font": {}}}
        corrector = FormatCorrector(template_path=None, config=config)
        corrector._detected_language = "korean"

        doc = Document()
        para = doc.add_paragraph()
        run = para.add_run("테스트")
        font_rules = {
            "chinese": "宋体",
            "korean": "Batang",
            "english": "Times New Roman",
        }
        style_rules = {}

        corrector._set_run_font(run, font_rules, style_rules)
        assert run.font.name == "Times New Roman"
