"""兼容性 shim - 请使用新的导入路径"""
import warnings

warnings.warn("此导入路径已弃用，请使用新的路径: infrastructure.parsers.reference_formatter", DeprecationWarning, stacklevel=2)

from ..infrastructure.parsers.reference_formatter import ReferenceFormatter  # noqa: E402

__all__ = ["ReferenceFormatter"]
