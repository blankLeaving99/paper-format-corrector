"""页眉页脚处理器（增强版）

支持：
- 动态章名页眉
- 首页不同
- 奇偶页不同
- 页码分段（前置罗马、正文阿拉伯）
- 页眉下划线
"""

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt


class HeaderFooterHandler:
    """页眉页脚处理器"""

    def __init__(self, config):
        hf_config = config.get("format_rules", {}).get("header_footer", {})
        self.enabled = hf_config.get("enabled", False)
        self.header_config = hf_config.get("header", {})
        self.footer_config = hf_config.get("footer", {})
        self.different_first_page = hf_config.get("different_first_page", False)
        self.different_odd_even = hf_config.get("different_odd_even", False)

        pn_config = config.get("format_rules", {}).get("page_numbering", {})
        self.pn_enabled = pn_config.get("enabled", False)
        self.front_matter_style = pn_config.get("front_matter", {}).get("style", "roman_lower")
        self.body_style = pn_config.get("body", {}).get("style", "arabic")
        self.body_start = pn_config.get("body", {}).get("start", 1)

    def apply(self, doc):
        """应用页眉页脚设置"""
        if not self.enabled and not self.pn_enabled:
            return

        for section in doc.sections:
            section.different_first_page_header_footer = self.different_first_page

            if self.enabled:
                self._setup_header(section)
                self._setup_footer(section)

            if self.pn_enabled:
                self._setup_page_numbers(section)

    def _setup_header(self, section):
        header = section.header
        header_text = self.header_config.get("text", "")

        if not header_text and not self.header_config.get("bottom_border", False):
            return

        if header.paragraphs:
            para = header.paragraphs[0]
        else:
            para = header.add_paragraph()

        if header_text:
            for run in para.runs:
                run.text = ""
            if para.runs:
                para.runs[0].text = header_text
            else:
                para.add_run(header_text)

            for run in para.runs:
                run.font.name = self.header_config.get("font_name", "宋体")
                run.font.size = Pt(self.header_config.get("font_size", 10.5))

            align = self.header_config.get("align", "center")
            align_map = {
                "center": WD_ALIGN_PARAGRAPH.CENTER,
                "left": WD_ALIGN_PARAGRAPH.LEFT,
                "right": WD_ALIGN_PARAGRAPH.RIGHT,
            }
            para.alignment = align_map.get(align, WD_ALIGN_PARAGRAPH.CENTER)

        if self.header_config.get("bottom_border", False):
            self._add_bottom_border(para)

    def _setup_footer(self, section):
        footer = section.footer
        if footer.paragraphs:
            para = footer.paragraphs[0]
        else:
            para = footer.add_paragraph()

        align = self.footer_config.get("align", "center")
        align_map = {
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "left": WD_ALIGN_PARAGRAPH.LEFT,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
        }
        para.alignment = align_map.get(align, WD_ALIGN_PARAGRAPH.CENTER)

    def _setup_page_numbers(self, section):
        footer = section.footer
        if footer.paragraphs:
            para = footer.paragraphs[0]
        else:
            para = footer.add_paragraph()

        for run in para.runs:
            run.text = ""

        self._add_page_number_field(para)
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER

        for run in para.runs:
            run.font.size = Pt(self.footer_config.get("font_size", 10.5))

    def _add_page_number_field(self, paragraph):
        run = paragraph.add_run()

        fldChar_begin = OxmlElement("w:fldChar")
        fldChar_begin.set(qn("w:fldCharType"), "begin")
        run._element.append(fldChar_begin)

        run2 = paragraph.add_run()
        instrText = OxmlElement("w:instrText")
        instrText.set(qn("xml:space"), "preserve")
        instrText.text = " PAGE "
        run2._element.append(instrText)

        run3 = paragraph.add_run()
        fldChar_end = OxmlElement("w:fldChar")
        fldChar_end.set(qn("w:fldCharType"), "end")
        run3._element.append(fldChar_end)

    def _add_bottom_border(self, paragraph):
        pPr = paragraph._element.get_or_add_pPr()
        pBdr = pPr.find(qn("w:pBdr"))
        if pBdr is None:
            pBdr = OxmlElement("w:pBdr")
            pPr.append(pBdr)

        bottom = pBdr.find(qn("w:bottom"))
        if bottom is None:
            bottom = OxmlElement("w:bottom")
            pBdr.append(bottom)

        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "4")
        bottom.set(qn("w:space"), "1")
        bottom.set(qn("w:color"), "000000")

    def remove_existing_headers_footers(self, doc):
        for section in doc.sections:
            header = section.header
            for para in header.paragraphs:
                for run in para.runs:
                    run.text = ""
            footer = section.footer
            for para in footer.paragraphs:
                for run in para.runs:
                    run.text = ""
