"""兼容性 shim - 请使用新的导入路径"""
import warnings

warnings.warn("此导入路径已弃用，请使用新的路径: parsers.section_parser", DeprecationWarning, stacklevel=2)

from ....core.document.parser.section_parser import SectionDetector, detect_language  # noqa: E402
from ....core.document.parser.section_types import SectionType  # noqa: E402

__all__ = ["SectionDetector", "SectionType", "detect_language"]
