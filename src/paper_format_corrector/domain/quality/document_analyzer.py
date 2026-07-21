"""兼容性 shim - 请使用新的导入路径"""
import warnings

warnings.warn("此导入路径已弃用，请使用新的路径: quality.document_analyzer", DeprecationWarning, stacklevel=2)

from ...domain.quality.document_analyzer import DocumentAnalyzer  # noqa: E402

__all__ = ["DocumentAnalyzer"]
