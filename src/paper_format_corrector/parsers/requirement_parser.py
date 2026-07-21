"""兼容性 shim - 请使用新的导入路径"""
import warnings

warnings.warn("此导入路径已弃用，请使用新的路径: infrastructure.parsers.requirement_parser", DeprecationWarning, stacklevel=2)

from ..infrastructure.parsers.requirement_parser import FONT_SIZE_MAP, RequirementParser  # noqa: E402

__all__ = ["RequirementParser", "FONT_SIZE_MAP"]
