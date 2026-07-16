"""表格格式处理器

处理文档中的表格：
- 表头行/数据行区分格式
- 单元格字体/字号/对齐
- 单元格垂直居中
- 表格边框（全边框/三线表）
- 表格宽度
- 表格内段落格式
"""

from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

from ...shared.utils.docx_utils import set_east_asian_font


class TableHandler:
    """表格格式处理器"""

    def __init__(self, config):
        ft = config.get("format_rules", {})
        self.font_rules = ft.get("font", {})
        self.table_config = ft.get("tables", {})
        self.body_config = ft.get("body_text", {})

        self.cn_font = self.font_rules.get("chinese", "宋体")
        self.en_font = self.font_rules.get("english", "Times New Roman")
        self.default_font_size = self.table_config.get("font_size", 10.5)
        self.header_bold = self.table_config.get("header_bold", True)
        self.header_font_size = self.table_config.get("header_font_size", self.default_font_size)
        self.table_style = ft.get("_table_style", None)

    def format_all_tables(self, doc):
        """格式化文档中所有表格"""
        count = 0
        for table in doc.tables:
            self._format_table(table)
            count += 1
        return count

    def _format_table(self, table):
        """格式化单个表格"""
        # 表格居中
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        # 设置表格宽度
        table_width = self.table_config.get("width")
        if table_width:
            self._set_table_width(table, table_width)

        # 应用表格样式（三线表/全边框）
        if self.table_style == "three_line":
            self.remove_table_borders(table)
        elif self.table_style == "full_border":
            self.set_table_borders(table)

        for row_idx, row in enumerate(table.rows):
            is_header = row_idx == 0
            for col_idx, cell in enumerate(row.cells):
                self._format_cell(cell, row_idx, col_idx, is_header,
                                  len(table.rows), len(table.columns))

    def _format_cell(self, cell, row_idx, col_idx, is_header, total_rows, total_cols):
        """格式化单个单元格"""
        # 垂直居中
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

        for para in cell.paragraphs:
            self._format_cell_paragraph(para, is_header)

    def _format_cell_paragraph(self, paragraph, is_header):
        """格式化单元格内段落"""
        font_size = self.header_font_size if is_header else self.default_font_size
        bold = self.header_bold if is_header else False

        # 设置字体
        for run in paragraph.runs:
            run.font.name = self.en_font
            set_east_asian_font(run, self.cn_font)
            run.font.size = Pt(font_size)
            run.font.bold = bold

        # 从 config 读取对齐方式（表头默认居中，数据行默认居中）
        align_config = self.table_config.get("alignment", {})
        if is_header:
            align = align_config.get("header", "center")
        else:
            align = align_config.get("body", "center")

        align_map = {
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "left": WD_ALIGN_PARAGRAPH.LEFT,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
            "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        }
        paragraph.alignment = align_map.get(align, WD_ALIGN_PARAGRAPH.CENTER)

        # 行距
        paragraph.paragraph_format.line_spacing = 1.0  # 表格内单倍行距
        paragraph.paragraph_format.space_before = Pt(2)
        paragraph.paragraph_format.space_after = Pt(2)

    def _get_or_create_tblPr(self, table):
        """获取表格属性元素，不存在时创建并挂载"""
        tbl = table._tbl
        tblPr = tbl.tblPr
        if tblPr is None:
            tblPr = OxmlElement("w:tblPr")
            tbl.insert(0, tblPr)
        return tblPr

    def set_table_borders(self, table):
        """设置表格边框"""
        tblPr = self._get_or_create_tblPr(table)

        borders = OxmlElement("w:tblBorders")
        for border_name in ("top", "left", "bottom", "right", "insideH", "insideV"):
            border = OxmlElement(f"w:{border_name}")
            border.set(qn("w:val"), "single")
            border.set(qn("w:sz"), "4")
            border.set(qn("w:space"), "0")
            border.set(qn("w:color"), "000000")
            borders.append(border)

        # 清除旧边框
        old_borders = tblPr.find(qn("w:tblBorders"))
        if old_borders is not None:
            tblPr.remove(old_borders)
        tblPr.append(borders)

    def remove_table_borders(self, table):
        """三线表：清除所有边框，然后按行级设置三条线。

        正确三线表 = 表头顶线(粗) + 表头底线(细) + 表尾底线(粗)
        """
        tblPr = self._get_or_create_tblPr(table)

        # 先清除表格级所有边框
        borders = OxmlElement("w:tblBorders")
        for border_name in ("top", "left", "bottom", "right", "insideH", "insideV"):
            border = OxmlElement(f"w:{border_name}")
            border.set(qn("w:val"), "none")
            border.set(qn("w:sz"), "0")
            border.set(qn("w:space"), "0")
            border.set(qn("w:color"), "auto")
            borders.append(border)

        old_borders = tblPr.find(qn("w:tblBorders"))
        if old_borders is not None:
            tblPr.remove(old_borders)
        tblPr.append(borders)

        if not table.rows:
            return

        # 通过行级边框实现三线表
        # 第一行：顶线（粗 sz=12）+ 表头底线（细 sz=6）
        self._set_row_border(table.rows[0], "top", sz="12")
        self._set_row_border(table.rows[0], "bottom", sz="6")

        # 最后一行：底线（粗 sz=12）
        if len(table.rows) > 1:
            self._set_row_border(table.rows[-1], "bottom", sz="12")

    def _set_row_border(self, row, position, sz="6"):
        """为指定行设置单元格级边框（支持合并单元格）。"""
        for tc in row._tr.findall(qn("w:tc")):
            tcPr = tc.find(qn("w:tcPr"))
            if tcPr is None:
                tcPr = OxmlElement("w:tcPr")
                tc.insert(0, tcPr)

            tcBorders = tcPr.find(qn("w:tcBorders"))
            if tcBorders is None:
                tcBorders = OxmlElement("w:tcBorders")
                tcPr.append(tcBorders)

            border = OxmlElement(f"w:{position}")
            border.set(qn("w:val"), "single")
            border.set(qn("w:sz"), sz)
            border.set(qn("w:space"), "0")
            border.set(qn("w:color"), "000000")

            old = tcBorders.find(qn(f"w:{position}"))
            if old is not None:
                tcBorders.remove(old)
            tcBorders.append(border)

    def _set_table_width(self, table, width):
        """设置表格宽度"""
        tblPr = self._get_or_create_tblPr(table)
        tblW = OxmlElement("w:tblW")
        tblW.set(qn("w:w"), str(int(width)))
        tblW.set(qn("w:type"), "dxa")
        old_w = tblPr.find(qn("w:tblW"))
        if old_w is not None:
            tblPr.remove(old_w)
        tblPr.append(tblW)
