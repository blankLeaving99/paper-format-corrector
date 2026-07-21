"""兼容性 shim - 请使用新的导入路径"""
import warnings

warnings.warn("此导入路径已弃用，请使用新的路径: infrastructure.parsers.ai_doc_generator", DeprecationWarning, stacklevel=2)

from ..infrastructure.parsers.ai_doc_generator import AIDocGenerator, ChatSession  # noqa: E402

__all__ = ["AIDocGenerator", "ChatSession"]
