"""兼容性 shim - 请使用新的导入路径"""
import warnings

warnings.warn("此导入路径已弃用，请使用新的路径: infrastructure.quality.rule_engine", DeprecationWarning, stacklevel=2)

from ..infrastructure.quality.rule_engine import RuleEngine  # noqa: E402

__all__ = ["RuleEngine"]
