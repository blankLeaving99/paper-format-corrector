"""规则解析器测试"""

import pytest

from paper_format_corrector.parsers.rule_parser import (
    CHINESE_SIZE_MAP,
    RuleParser,
    parse_requirement_text,
    parse_requirement_file,
)


class TestRuleParser:
    """RuleParser 测试"""

    def setup_method(self):
        self.parser = RuleParser()

    def test_parse_empty_text(self):
        """测试空文本"""
        result = self.parser.parse("")
        assert result == {"format_rules": {}}

    def test_parse_body_font(self):
        """测试解析正文字体"""
        text = "正文：宋体，小四号字"
        result = self.parser.parse(text)

        assert "format_rules" in result
        assert "body_text" in result["format_rules"]
        assert result["format_rules"]["body_text"]["chinese_font"] == "宋体"
        assert result["format_rules"]["body_text"]["font_size"] == 12

    def test_parse_heading_font(self):
        """测试解析标题字体"""
        text = "一级标题：黑体，三号字，居中，加粗"
        result = self.parser.parse(text)

        assert "headings" in result["format_rules"]
        assert "heading1" in result["format_rules"]["headings"]
        h1 = result["format_rules"]["headings"]["heading1"]
        assert h1["chinese_font"] == "黑体"
        assert h1["font_size"] == 16
        assert h1["align"] == "center"
        assert h1["bold"] is True

    def test_parse_line_spacing(self):
        """测试解析行距"""
        text = "正文：1.5倍行距"
        result = self.parser.parse(text)

        assert result["format_rules"]["body_text"]["line_spacing"] == 1.5

    def test_parse_exact_line_spacing(self):
        """测试解析固定行距"""
        text = "正文：固定值20磅"
        result = self.parser.parse(text)

        assert result["format_rules"]["body_text"]["line_spacing"]["type"] == "exact"
        assert result["format_rules"]["body_text"]["line_spacing"]["value"] == 20

    def test_parse_first_line_indent(self):
        """测试解析首行缩进"""
        text = "正文：首行缩进2字符"
        result = self.parser.parse(text)

        assert result["format_rules"]["body_text"]["first_line_indent"] == 2

    def test_parse_margins(self):
        """测试解析页边距"""
        text = "页边距：上下2.54cm，左右3.17cm"
        result = self.parser.parse(text)

        margins = result["format_rules"]["margins"]
        assert margins["top"] == 2.54
        assert margins["bottom"] == 2.54
        assert margins["left"] == 3.17
        assert margins["right"] == 3.17

    def test_parse_individual_margins(self):
        """测试解析单独页边距"""
        text = "上边距2.5cm 下边距2.5cm 左边距3cm 右边距3cm"
        result = self.parser.parse(text)

        margins = result["format_rules"]["margins"]
        assert margins["top"] == 2.5
        assert margins["bottom"] == 2.5
        assert margins["left"] == 3
        assert margins["right"] == 3

    def test_parse_bold(self):
        """测试解析加粗"""
        text = "一级标题：加粗"
        result = self.parser.parse(text)

        assert result["format_rules"]["headings"]["heading1"]["bold"] is True

    def test_parse_no_indent(self):
        """测试解析不缩进"""
        text = "摘要：不缩进"
        result = self.parser.parse(text)

        assert result["format_rules"]["abstract"]["first_line_indent"] == 0

    def test_parse_multiple_rules(self):
        """测试解析多条规则"""
        text = """
正文：宋体，小四号字，1.5倍行距，首行缩进2字符
一级标题：黑体，三号字，居中，加粗
二级标题：黑体，四号字，左对齐
页边距：上下2.54cm，左右3.17cm
"""
        result = self.parser.parse(text)

        # 检查正文
        body = result["format_rules"]["body_text"]
        assert body["chinese_font"] == "宋体"
        assert body["font_size"] == 12
        assert body["line_spacing"] == 1.5
        assert body["first_line_indent"] == 2

        # 检查标题
        assert "heading1" in result["format_rules"]["headings"]
        assert "heading2" in result["format_rules"]["headings"]

        # 检查页边距
        assert "margins" in result["format_rules"]

    def test_parse_english_text(self):
        """测试解析英文文本"""
        text = "Body: Times New Roman, 12pt, 1.5 line spacing"
        result = self.parser.parse(text)

        body = result["format_rules"]["body_text"]
        assert body["english_font"] == "Times New Roman"
        assert body["font_size"] == 12
        assert body["line_spacing"] == 1.5


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_parse_requirement_text(self):
        """测试 parse_requirement_text"""
        text = "正文：宋体，小四号字"
        result = parse_requirement_text(text)

        assert "format_rules" in result
        assert result["format_rules"]["body_text"]["chinese_font"] == "宋体"

    def test_parse_requirement_file_not_found(self):
        """测试文件不存在"""
        with pytest.raises(FileNotFoundError):
            parse_requirement_file("nonexistent.txt")


class TestChineseSizeMap:
    """中文字号映射测试"""

    def test_all_sizes_defined(self):
        """测试所有中文字号都有定义"""
        expected_sizes = [
            "初号", "小初", "一号", "小一",
            "二号", "小二", "三号", "小三",
            "四号", "小四", "五号", "小五",
        ]
        for size in expected_sizes:
            assert size in CHINESE_SIZE_MAP
            assert CHINESE_SIZE_MAP[size] > 0
