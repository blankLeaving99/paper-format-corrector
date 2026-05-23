"""基础测试套件"""

import os
import sys

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))



def test_section_detector_import():
    from paper_format_corrector.parsers.section_detector import SectionType, detect_language
    assert SectionType.CHAPTER is not None
    assert detect_language("这是中文") == "chinese"
    assert detect_language("This is English") == "english"
    assert detect_language("これは日本語") == "japanese"


def test_detect_language():
    from paper_format_corrector.parsers.section_detector import detect_language
    assert detect_language("") == "unknown"
    assert detect_language("12345") == "unknown"
    assert detect_language("hello world test") == "english"
    assert detect_language("你好世界测试") == "chinese"


def test_requirement_parser_import():
    from paper_format_corrector.parsers.requirement_parser import FONT_SIZE_MAP
    assert "小四" in FONT_SIZE_MAP
    assert FONT_SIZE_MAP["小四"] == 12
    assert FONT_SIZE_MAP["二号"] == 22


def test_quality_scorer_import():
    from paper_format_corrector.quality.quality_scorer import QualityScorer
    assert QualityScorer is not None


def test_rule_engine_import():
    from paper_format_corrector.quality.rule_engine import RuleEngine
    engine = RuleEngine()
    assert len(engine.checkers) > 0


def test_plugin_manager():
    from paper_format_corrector.infra.plugin_manager import PluginManager
    manager = PluginManager({})
    plugins = manager.list_plugins()
    assert len(plugins) == 0


def test_cross_reference_import():
    from paper_format_corrector.parsers.cross_reference import CrossReferenceUpdater
    updater = CrossReferenceUpdater()
    assert updater._update_text("如图1所示") == "如图1所示"


def test_image_handler_import():
    from paper_format_corrector.handlers.image_handler import ImageHandler
    handler = ImageHandler({})
    assert handler.center is True


def test_diff_reporter_import():
    from paper_format_corrector.quality.diff_reporter import DiffReporter
    reporter = DiffReporter()
    assert reporter is not None


def test_logger_import():
    from paper_format_corrector.infra.logger import Logger
    logger = Logger(level="DEBUG", color=False)
    logger.info("test message")


def test_cover_page_generator_import():
    from paper_format_corrector.generators.cover_page_generator import CoverPageGenerator
    gen = CoverPageGenerator()
    assert gen is not None


def test_format_exporter_import():
    from paper_format_corrector.core.format_exporter import FormatExporter
    FormatExporter()
    assert "pdf" in FormatExporter.SUPPORTED_FORMATS
    assert "html" in FormatExporter.SUPPORTED_FORMATS


def test_table_handler_import():
    from paper_format_corrector.handlers.table_handler import TableHandler
    handler = TableHandler({})
    assert handler is not None


def test_ref_auto_complete_import():
    from paper_format_corrector.parsers.ref_auto_complete import RefAutoComplete
    rc = RefAutoComplete()
    assert rc is not None
