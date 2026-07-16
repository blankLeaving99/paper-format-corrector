"""兼容性 shim - 请使用新的导入路径"""
import warnings
warnings.warn("此导入路径已弃用，请使用新的路径: infrastructure.parsers.section_parser", DeprecationWarning, stacklevel=2)

from ..infrastructure.parsers.section_parser import SectionDetector, detect_language
from ..infrastructure.parsers.section_types import SectionType

__all__ = ["SectionDetector", "SectionType", "detect_language"]
