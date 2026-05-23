"""插件架构管理器

将各功能模块注册为插件，支持：
- 插件注册/注销
- 按优先级顺序执行
- 启用/禁用插件
- 插件间数据传递
"""

import importlib
from pathlib import Path


class Plugin:
    """插件基类"""

    name = "base_plugin"
    description = ""
    priority = 100  # 数值越小优先级越高
    enabled = True

    def __init__(self, config):
        self.config = config

    def process(self, doc, context):
        """处理文档，返回更新后的context"""
        raise NotImplementedError

    def get_report(self):
        """返回处理报告"""
        return {}


class PluginManager:
    """插件管理器"""

    def __init__(self, config):
        self.config = config
        self.plugins = []

    def register(self, plugin_class):
        """注册插件"""
        plugin = plugin_class(self.config)
        self.plugins.append(plugin)
        self.plugins.sort(key=lambda p: p.priority)

    def unregister(self, plugin_name):
        """注销插件"""
        self.plugins = [p for p in self.plugins if p.name != plugin_name]

    def enable(self, plugin_name):
        """启用插件"""
        for p in self.plugins:
            if p.name == plugin_name:
                p.enabled = True

    def disable(self, plugin_name):
        """禁用插件"""
        for p in self.plugins:
            if p.name == plugin_name:
                p.enabled = False

    def run_all(self, doc, context=None):
        """按优先级顺序执行所有已启用的插件"""
        if context is None:
            context = {}

        for plugin in self.plugins:
            if not plugin.enabled:
                continue
            try:
                context = plugin.process(doc, context)
            except Exception as e:
                context.setdefault("errors", []).append(
                    f"插件 {plugin.name} 执行失败: {e}"
                )

        return context

    def get_reports(self):
        """获取所有插件的报告"""
        reports = {}
        for plugin in self.plugins:
            if plugin.enabled:
                reports[plugin.name] = plugin.get_report()
        return reports

    def list_plugins(self):
        """列出所有插件"""
        return [
            {
                "name": p.name,
                "description": p.description,
                "priority": p.priority,
                "enabled": p.enabled,
            }
            for p in self.plugins
        ]


# ========== 内置插件 ==========

class PageSetupPlugin(Plugin):
    name = "page_setup"
    description = "页面设置（边距、纸张）"
    priority = 10

    def process(self, doc, context):
        from docx.shared import Cm
        margins = self.config.get("format_rules", {}).get("margins", {})
        if margins:
            for section in doc.sections:
                section.top_margin = Cm(margins.get("top", 2.54))
                section.bottom_margin = Cm(margins.get("bottom", 2.54))
                section.left_margin = Cm(margins.get("left", 3.17))
                section.right_margin = Cm(margins.get("right", 3.17))
        return context


class TableFormatPlugin(Plugin):
    name = "table_format"
    description = "表格格式化"
    priority = 50

    def process(self, doc, context):
        from table_handler import TableHandler
        handler = TableHandler(self.config)
        count = handler.format_all_tables(doc)
        context["tables_formatted"] = count
        return context


class ImagePlugin(Plugin):
    name = "image_handler"
    description = "图片处理（居中、调整大小）"
    priority = 55

    def process(self, doc, context):
        from image_handler import ImageHandler
        handler = ImageHandler(self.config)
        count = handler.process_all_images(doc)
        context["images_processed"] = count
        return context


class TOCPlugin(Plugin):
    name = "toc"
    description = "目录生成"
    priority = 80

    def process(self, doc, context):
        from toc_handler import TOCHandler
        handler = TOCHandler(self.config)
        if handler.enabled and not handler.has_toc(doc):
            handler.insert_toc(doc)
            context["toc_inserted"] = True
        return context


class HeaderFooterPlugin(Plugin):
    name = "header_footer"
    description = "页眉页脚处理"
    priority = 90

    def process(self, doc, context):
        from header_footer_handler import HeaderFooterHandler
        handler = HeaderFooterHandler(self.config)
        handler.apply(doc)
        return context


class QualityScorePlugin(Plugin):
    name = "quality_score"
    description = "格式质量评分"
    priority = 100

    def process(self, doc, context):
        # 需要在保存后执行，这里只标记
        context["needs_quality_score"] = True
        return context


def register_default_plugins(manager):
    """注册所有默认插件"""
    manager.register(PageSetupPlugin)
    manager.register(TableFormatPlugin)
    manager.register(ImagePlugin)
    manager.register(TOCPlugin)
    manager.register(HeaderFooterPlugin)
    manager.register(QualityScorePlugin)
