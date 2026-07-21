"""兼容性 shim - 请使用新的导入路径"""
import warnings

warnings.warn("此导入路径已弃用，请使用新的路径: infra.adapters.docx_adapter", DeprecationWarning, stacklevel=2)

from ...infrastructure.adapters.docx_adapter import StyleExtractor  # noqa: E402

__all__ = ["StyleExtractor"]
