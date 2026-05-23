import re

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt


class FigureTableHandler:
    """图表编号与格式处理"""

    def __init__(self, config):
        ft_config = config.get("format_rules", {})
        self.fig_config = ft_config.get("figures", {})
        self.tab_config = ft_config.get("tables", {})
        self.font_rules = ft_config.get("font", {})
        self.auto_detect = config.get("auto_detect", {})

        self.fig_pattern = re.compile(
            self.auto_detect.get("figure_caption_pattern", r"^图\s*\d")
        )
        self.tab_pattern = re.compile(
            self.auto_detect.get("table_caption_pattern", r"^表\s*\d")
        )

        # 统计信息
        self.fig_count = 0
        self.tab_count = 0
        self.current_chapter = 0
        self.issues = []

    def reset(self):
        self.fig_count = 0
        self.tab_count = 0
        self.current_chapter = 0
        self.issues = []

    def process_paragraph(self, paragraph, section_type, extra_info):
        """处理图表标题段落"""
        text = paragraph.text.strip()

        if self.fig_pattern.match(text):
            self._handle_caption(paragraph, text, "figure")
        elif self.tab_pattern.match(text):
            self._handle_caption(paragraph, text, "table")

    def update_chapter(self, chapter_num):
        """更新当前章节号"""
        self.current_chapter = chapter_num

    def _handle_caption(self, paragraph, text, kind):
        """处理单个图表标题"""
        config = self.fig_config if kind == "figure" else self.tab_config
        label = config.get("label", "图" if kind == "figure" else "表")
        numbering = config.get("numbering", "chapter")
        separator = config.get("separator", "-")
        font_size = config.get("font_size", 10.5)
        align = config.get("align", "center")

        if kind == "figure":
            self.fig_count += 1
            count = self.fig_count
        else:
            self.tab_count += 1
            count = self.tab_count

        # 生成正确的编号
        if numbering == "chapter" and self.current_chapter > 0:
            correct_num = f"{self.current_chapter}{separator}{count}"
        else:
            correct_num = str(count)

        # 提取现有标题文本（去掉编号前缀）
        # 使用 re.escape(label) 支持 "Fig." 等含特殊字符的标签
        escaped_label = re.escape(label)
        caption_text = re.sub(rf"^{escaped_label}\s*\d+[\-\.]\d+\s*", "", text)
        caption_text = re.sub(rf"^{escaped_label}\s*\d+\.?\s*", "", caption_text)

        # 重建段落内容
        correct_label = f"{label}{correct_num} {caption_text.strip()}"

        # 检查是否需要修正
        normalized_text = re.sub(r"\s+", "", text)
        normalized_correct = re.sub(r"\s+", "", correct_label)
        if normalized_text != normalized_correct:
            self.issues.append(
                f"图表编号修正: '{text}' -> '{correct_label}'"
            )

        # 清空并重写段落
        for run in paragraph.runs:
            run.text = ""
        if paragraph.runs:
            paragraph.runs[0].text = correct_label
        else:
            paragraph.add_run(correct_label)

        # 应用格式
        for run in paragraph.runs:
            run.font.name = self.font_rules.get("english", "Times New Roman")
            self._set_east_asian_font(run, self.font_rules.get("chinese", "宋体"))
            run.font.size = Pt(font_size)
            run.font.bold = False

        align_map = {
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "left": WD_ALIGN_PARAGRAPH.LEFT,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
        }
        paragraph.alignment = align_map.get(align, WD_ALIGN_PARAGRAPH.CENTER)
        paragraph.paragraph_format.space_before = Pt(6)
        paragraph.paragraph_format.space_after = Pt(6)

    def get_issues(self):
        return self.issues

    def _set_east_asian_font(self, run, font_name):
        rpr = run._element.get_or_add_rPr()
        rFonts = rpr.find(qn("w:rFonts"))
        if rFonts is None:
            rFonts = run._element.makeelement(qn("w:rFonts"), {})
            rpr.insert(0, rFonts)
        rFonts.set(qn("w:eastAsia"), font_name)
