"""兼容性 shim - 请使用新的导入路径"""
import warnings
warnings.warn("此导入路径已弃用，请使用新的路径: infrastructure.handlers.toc_handler", DeprecationWarning, stacklevel=2)

from ..infrastructure.handlers.toc_handler import TOCHandler

__all__ = ["TOCHandler"]
