"""兼容性 shim - 请使用新的导入路径"""
import warnings

warnings.warn("此导入路径已弃用，请使用新的路径: infrastructure.parsers.rule_parser", DeprecationWarning, stacklevel=2)

from ..infrastructure.parsers.rule_parser import (  # noqa: E402
    ALIGNMENT_MAP,
    CHINESE_SIZE_MAP,
    FONT_PATTERNS,
    LINE_SPACING_MAP,
    RuleParser,
    parse_requirement_file,
    parse_requirement_text,
)

__all__ = [
    "RuleParser",
    "CHINESE_SIZE_MAP",
    "FONT_PATTERNS",
    "ALIGNMENT_MAP",
    "LINE_SPACING_MAP",
    "parse_requirement_text",
    "parse_requirement_file",
]
