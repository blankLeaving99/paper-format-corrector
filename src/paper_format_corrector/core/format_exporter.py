"""兼容性 shim - 请使用新的导入路径"""
import warnings
warnings.warn("此导入路径已弃用，请使用新的路径: infrastructure.exporters.format_exporter", DeprecationWarning, stacklevel=2)

from ..infrastructure.exporters.format_exporter import FormatExporter

__all__ = ["FormatExporter"]
