"""兼容性 shim - 请使用新的导入路径"""
import warnings

warnings.warn("此导入路径已弃用，请使用新的路径: infrastructure.generators.cover_generator", DeprecationWarning, stacklevel=2)

from ..infrastructure.generators.cover_generator import CoverPageGenerator  # noqa: E402

__all__ = ["CoverPageGenerator"]
