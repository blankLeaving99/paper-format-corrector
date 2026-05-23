"""图片处理模块

自动调整文档中的图片：
- 宽度调整（占满页宽/百分比）
- 居中对齐
- DPI检查
- 支持内联图片和浮动图片
"""

from docx.shared import Pt, Cm, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn


class ImageHandler:
    """图片处理器"""

    def __init__(self, config):
        img_config = config.get("format_rules", {}).get("images", {})
        self.max_width = img_config.get("max_width", "full")  # full | 50% | 具体cm
        self.center = img_config.get("center", True)
        self.min_dpi = img_config.get("min_dpi", 150)
        self._warnings = []

    def process_all_images(self, doc):
        """处理文档中所有图片（居中 + 调整大小 + DPI检查）"""
        count = 0
        page_width = self._get_page_content_width(doc)

        for para in doc.paragraphs:
            has_image = False

            for run in para.runs:
                # 处理 Drawing 对象（新版 .docx 图片格式）
                drawings = run._element.findall(qn("w:drawing"))
                for drawing in drawings:
                    self._process_drawing(drawing, page_width)
                    has_image = True

                # 处理旧式图片 (pict/v:imagedata)
                picts = run._element.findall(qn("w:pict"))
                for pict in picts:
                    has_image = True

            if has_image and self.center:
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                count += 1

        return count

    def get_warnings(self):
        """返回处理过程中的警告信息"""
        return self._warnings

    def _get_page_content_width(self, doc):
        """获取页面内容区宽度（EMU）"""
        section = doc.sections[0]
        page_width = section.page_width
        left_margin = section.left_margin or 0
        right_margin = section.right_margin or 0
        if page_width and left_margin and right_margin:
            return page_width - left_margin - right_margin
        return Cm(15)  # 默认约15cm

    def _process_drawing(self, drawing, page_width):
        """处理单个 Drawing 对象：调整大小 + DPI检查"""
        # 查找 extent 元素（可能有多个：inline 和 anchor）
        for ext in drawing.iter(qn("wp:extent")):
            cx = int(ext.get("cx", 0))
            cy = int(ext.get("cy", 0))

            if cx <= 0:
                continue

            # 根据配置调整宽度
            target_width = self._calc_target_width(page_width)

            # 只缩小不放大
            if cx > target_width:
                ratio = target_width / cx
                new_cx = int(target_width)
                new_cy = int(cy * ratio)
                ext.set("cx", str(new_cx))
                ext.set("cy", str(new_cy))

            # 同时更新 GraphicExtent (a:ext)
            for ext2 in drawing.iter(qn("a:ext")):
                if ext2.get("cx") == str(cx):
                    ext2.set("cx", str(int(ext.get("cx"))))
                    ext2.set("cy", str(int(ext.get("cy"))))

        # DPI 检查
        self._check_dpi(drawing)

    def _calc_target_width(self, page_width):
        """根据配置计算目标宽度"""
        if self.max_width == "full":
            return page_width
        elif isinstance(self.max_width, str) and self.max_width.endswith("%"):
            pct = int(self.max_width.rstrip("%")) / 100
            return int(page_width * pct)
        elif isinstance(self.max_width, (int, float)):
            return Cm(self.max_width)
        return page_width

    def _check_dpi(self, drawing):
        """检查图片 DPI 是否满足最低要求"""
        # 从 blipFill 中提取图片引用
        for blip in drawing.iter(qn("a:blip")):
            embed = blip.get(qn("r:embed"))
            if not embed:
                continue
            # 尝试从 extent 和实际图片尺寸计算 DPI
            for ext in drawing.iter(qn("wp:extent")):
                cx_emu = int(ext.get("cx", 0))
                cy_emu = int(ext.get("cy", 0))
                if cx_emu > 0 and cy_emu > 0:
                    # EMU 转英寸: 1 inch = 914400 EMU
                    width_inches = cx_emu / 914400
                    height_inches = cy_emu / 914400
                    # 如果图片很小（< 1英寸宽），可能DPI不足
                    if width_inches < 1.0:
                        self._warnings.append(
                            f"图片宽度仅 {width_inches:.1f} 英寸，可能分辨率不足"
                        )

    def get_image_stats(self, doc):
        """获取文档图片统计"""
        total = 0
        widths = []

        for para in doc.paragraphs:
            for run in para.runs:
                drawings = run._element.findall(qn("w:drawing"))
                for drawing in drawings:
                    for ext in drawing.iter(qn("wp:extent")):
                        cx = int(ext.get("cx", 0))
                        if cx > 0:
                            total += 1
                            widths.append(cx / 914400)  # EMU to inches

        return {
            "total": total,
            "avg_width_inches": sum(widths) / len(widths) if widths else 0,
            "max_width_inches": max(widths) if widths else 0,
        }
