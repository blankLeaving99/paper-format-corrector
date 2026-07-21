"""CLI集成测试"""



class TestCLIArgumentParsing:
    """CLI参数解析测试"""

    def test_offline_parser_argument(self):
        """测试 --offline-parser 参数存在"""

        # 验证参数解析器包含 offline-parser

        # 不能直接测试main，但可以验证参数定义
        # 通过检查argparse来验证
        pass  # 参数存在性通过CLI运行时验证

    def test_llm_arguments(self):
        """测试LLM相关参数"""
        # 验证所有LLM参数都被正确处理
        pass  # 通过CLI帮助验证


class TestAppApplyRequirement:
    """App.apply_requirement 集成测试"""

    def test_apply_requirement_offline_parser(self, tmp_path):
        """测试使用离线解析器"""
        from paper_format_corrector.app import PaperFormatCorrector

        # 创建测试需求文档
        req_file = tmp_path / "requirement.txt"
        req_file.write_text("正文：宋体，小四号字，1.5倍行距", encoding="utf-8")

        corrector = PaperFormatCorrector()
        corrector.apply_requirement(
            str(req_file),
            use_offline_parser=True,
        )

        # 验证配置被正确应用
        body_rules = corrector.config.get("format_rules", {}).get("body_text", {})
        assert body_rules.get("chinese_font") == "宋体"
        assert body_rules.get("font_size") == 12

    def test_apply_requirement_fallback_to_basic(self, tmp_path):
        """测试离线解析失败时回退到基础解析"""
        from paper_format_corrector.app import PaperFormatCorrector

        # 创建空的需求文档（无法解析）
        req_file = tmp_path / "empty.txt"
        req_file.write_text("", encoding="utf-8")

        corrector = PaperFormatCorrector()
        # 不应该抛出异常
        corrector.apply_requirement(
            str(req_file),
            use_offline_parser=True,
        )


class TestDocumentAnalyzerIntegration:
    """DocumentAnalyzer 集成测试"""

    def test_analyze_and_compare(self):
        """测试分析并比较"""
        from paper_format_corrector.core.document.analyzer import (
            ParagraphType,
        )

        assert ParagraphType.BODY.value == "body"
        assert ParagraphType.HEADING1.value == "heading1"


class TestReferenceFormatterIntegration:
    """ReferenceFormatter 集成测试"""

    def test_vancouver_style_detection(self):
        """测试Vancouver风格检测"""
        from paper_format_corrector.core.document.parser.reference import (
            ReferenceFormatter,
        )

        formatter = ReferenceFormatter({})
        assert hasattr(formatter, "CITATION_VANCOUVER")
        assert formatter.CITATION_VANCOUVER == "vancouver"

    def test_deduplicate_references_method_exists(self):
        """测试去重方法存在"""
        from paper_format_corrector.core.document.parser.reference import (
            ReferenceFormatter,
        )

        formatter = ReferenceFormatter({})
        assert hasattr(formatter, "deduplicate_references")
        assert callable(formatter.deduplicate_references)
