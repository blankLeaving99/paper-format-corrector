"""兼容性 shim - 请使用新的导入路径"""
import warnings

warnings.warn("此导入路径已弃用，请使用新的路径: infra.converters.file_formatter", DeprecationWarning, stacklevel=2)

from ...infrastructure.converters.file_formatter import FormatCorrector  # noqa: E402

__all__ = ["FormatCorrector"]
