"""兼容性 shim - 请使用新的导入路径"""
import warnings

warnings.warn("此导入路径已弃用，请使用新的路径: infrastructure.handlers.table_handler", DeprecationWarning, stacklevel=2)

from ..infrastructure.handlers.table_handler import TableHandler  # noqa: E402

__all__ = ["TableHandler"]
