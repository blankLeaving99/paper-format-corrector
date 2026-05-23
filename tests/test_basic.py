"""基础测试套件"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from pathlib import Path


def test_section_detector_import():
    from section_detector import SectionDetector, SectionType, detect_language
    assert SectionType.CHAPTER is not None
    assert detect_language("这是中文") == "chinese"
    assert detect_language("This is English") == "english"
    assert detect_language("これは日本語") == "japanese"


def test_detect_language():
    from section_detector import detect_language
    assert detect_language("") == "unknown"
    assert detect_language("12345") == "unknown"
    assert detect_language("hello world test") == "english"
    assert detect_language("你好世界测试") == "chinese"


def test_requirement_parser_import():
    from requirement_parser import RequirementParser, FONT_SIZE_MAP
    assert "小四" in FONT_SIZE_MAP
    assert FONT_SIZE_MAP["小四"] == 12
    assert FONT_SIZE_MAP["二号"] == 22


def test_quality_scorer_import():
    from quality_scorer import QualityScorer
    assert QualityScorer is not None


def test_rule_engine_import():
    from rule_engine import RuleEngine
    engine = RuleEngine()
    assert len(engine.checkers) > 0


def test_plugin_manager():
    from plugin_manager import PluginManager, Plugin
    manager = PluginManager({})
    plugins = manager.list_plugins()
    assert len(plugins) == 0


def test_cross_reference_import():
    from cross_reference import CrossReferenceUpdater
    updater = CrossReferenceUpdater()
    assert updater._update_text("如图1所示") == "如图1所示"


def test_image_handler_import():
    from image_handler import ImageHandler
    handler = ImageHandler({})
    assert handler.center is True


def test_diff_reporter_import():
    from diff_reporter import DiffReporter
    reporter = DiffReporter()
    assert reporter is not None


def test_logger_import():
    from logger import Logger, ProgressBar
    logger = Logger(level="DEBUG", color=False)
    logger.info("test message")


def test_cover_page_generator_import():
    from cover_page_generator import CoverPageGenerator
    gen = CoverPageGenerator()
    assert gen is not None


def test_format_exporter_import():
    from format_exporter import FormatExporter
    exporter = FormatExporter()
    assert "pdf" in FormatExporter.SUPPORTED_FORMATS
    assert "html" in FormatExporter.SUPPORTED_FORMATS


def test_table_handler_import():
    from table_handler import TableHandler
    handler = TableHandler({})
    assert handler is not None


def test_ref_auto_complete_import():
    from ref_auto_complete import RefAutoComplete
    rc = RefAutoComplete()
    assert rc is not None
