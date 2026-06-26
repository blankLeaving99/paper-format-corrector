from docx import Document
from docx.enum.style import WD_STYLE_TYPE


class StyleExtractor:
    """从模板中提取样式"""

    def __init__(self, template_path):
        self.template = Document(template_path)
        self.styles = {}

    def extract_all_styles(self):
        """提取所有段落样式信息"""
        for style in self.template.styles:
            if style.type == WD_STYLE_TYPE.PARAGRAPH:
                self.styles[style.name] = self._extract_paragraph_style(style)
        return self.styles

    def _extract_paragraph_style(self, style):
        style_info = {
            "name": style.name,
            "font_name": None,
            "font_size": None,
            "bold": False,
            "italic": False,
            "alignment": None,
            "line_spacing": None,
            "space_before": None,
            "space_after": None,
            "first_line_indent": None,
        }

        # 直接访问属性，不使用 truthiness 守卫
        # python-docx 的 style.font 总是返回 _Font 对象，不会是 None
        try:
            if style.font.name:
                style_info["font_name"] = style.font.name
            if style.font.size:
                style_info["font_size"] = style.font.size.pt
            if style.font.bold is not None:
                style_info["bold"] = style.font.bold
            if style.font.italic is not None:
                style_info["italic"] = style.font.italic
        except Exception:
            pass

        if style.paragraph_format:
            pf = style.paragraph_format
            if pf.alignment is not None:
                style_info["alignment"] = str(pf.alignment)
            if pf.line_spacing is not None:
                style_info["line_spacing"] = pf.line_spacing
            if pf.space_before is not None:
                style_info["space_before"] = pf.space_before.pt
            if pf.space_after is not None:
                style_info["space_after"] = pf.space_after.pt
            if pf.first_line_indent is not None:
                style_info["first_line_indent"] = pf.first_line_indent.pt

        return style_info

    def extract_page_margins(self):
        """提取页面边距"""
        if not self.template.sections:
            return {}
        section = self.template.sections[0]
        return {
            "top": section.top_margin.cm,
            "bottom": section.bottom_margin.cm,
            "left": section.left_margin.cm,
            "right": section.right_margin.cm,
        }

    def extract_character_styles(self):
        """提取字符样式信息"""
        char_styles = {}
        for style in self.template.styles:
            if style.type == WD_STYLE_TYPE.CHARACTER:
                try:
                    info = {
                        "name": style.name,
                        "font_name": style.font.name,
                        "font_size": style.font.size.pt if style.font.size else None,
                        "bold": style.font.bold,
                        "italic": style.font.italic,
                    }
                    char_styles[style.name] = info
                except Exception:
                    pass
        return char_styles

    def extract_numbering_definitions(self):
        """提取编号定义（列表样式）"""
        numbering_defs = {}
        try:
            numbering_part = self.template.part.numbering_part
            if numbering_part is None:
                return numbering_defs

            numbering_xml = numbering_part._element
            from docx.oxml.ns import qn

            for num in numbering_xml.findall(qn('w:num')):
                num_id = num.get(qn('w:numId'))
                abstract_ref = num.find(qn('w:abstractNumId'))
                if abstract_ref is not None:
                    abstract_id = abstract_ref.get(qn('w:val'))
                    numbering_defs[num_id] = {"abstract_id": abstract_id}
        except Exception:
            pass
        return numbering_defs
