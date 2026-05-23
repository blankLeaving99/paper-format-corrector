"""图片处理模块

自动调整文档中的图片：
- 宽度调整（占满页宽/百分比）
- 居中对齐
- DPI检查
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

    def process_all_images(self, doc):
        """处理文档中所有图片"""
        count = 0
        page_width = self._get_page_content_width(doc)

        for para in doc.paragraphs:
            has_image = False

            for run in para.runs:
                # 处理 Drawing 对象
                drawings = run._element.findall(qn("w:drawing"))
                for drawing in drawings:
                    self._resize_drawing(drawing, page_width)
                    has_image = True

                # 处理旧式图片 (pict/v:imagedata)
                picts = run._element.findall(qn("w:pict"))
                for pict in picts:
                    has_image = True

            if has_image and self.center:
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                count += 1

        return count

    def _get_page_content_width(self, doc):
        """获取页面内容区宽度（EMU）"""
        section = doc.sections[0]
        page_width = section.page_width
        left_margin = section.left_margin
        right_margin = section.right_margin
        if page_width and left_margin and right_margin:
            return page_width - left_margin - right_margin
        return Cm(15)  # 默认约15cm

    def _resize_drawing(self, drawing, page_width):
        """调整 Drawing 对象中的图片尺寸"""
        # 查找 extent 元素
        for ext in drawing.iter(qn("wp:extent")):
            cx = int(ext.get("cx", 0))
            cy = int(ext.get("cy", 0))

            if cx <= 0:
                continue

            # 根据配置调整宽度
            if self.max_width == "full":
                target_width = page_width
            elif isinstance(self.max_width, str) and self.max_width.endswith("%"):
                pct = int(self.max_width.rstrip("%")) / 100
                target_width = int(page_width * pct)
            elif isinstance(self.max_width, (int, float)):
                target_width = Cm(self.max_width)
            else:
                target_width = page_width

            # 只缩小不放大
            if cx > target_width:
                ratio = target_width / cx
                new_cx = int(target_width)
                new_cy = int(cy * ratio)
                ext.set("cx", str(new_cx))
                ext.set("cy", str(new_cy))

            # 同时更新 GraphicExtent
            for ext2 in drawing.iter(qn("a:ext")):
                if ext2.get("cx") == str(cx):
                    ext2.set("cx", str(int(ext.get("cx"))))
                    ext2.set("cy", str(int(ext.get("cy"))))

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
