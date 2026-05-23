"""文档组件处理器"""

from .figure_table_handler import FigureTableHandler
from .header_footer_handler import HeaderFooterHandler
from .image_handler import ImageHandler
from .table_handler import TableHandler
from .toc_handler import TOCHandler

__all__ = ["TableHandler", "HeaderFooterHandler", "ImageHandler", "FigureTableHandler", "TOCHandler"]
