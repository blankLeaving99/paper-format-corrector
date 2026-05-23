from docx import Document


class StyleExtractor:
    """从模板中提取样式"""

    def __init__(self, template_path):
        self.template = Document(template_path)
        self.styles = {}

    def extract_all_styles(self):
        for style in self.template.styles:
            if style.type == 1:  # 段落样式
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

        if style.font:
            if style.font.name:
                style_info["font_name"] = style.font.name
            if style.font.size:
                style_info["font_size"] = style.font.size.pt
            style_info["bold"] = style.font.bold
            style_info["italic"] = style.font.italic

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
        section = self.template.sections[0]
        return {
            "top": section.top_margin.cm,
            "bottom": section.bottom_margin.cm,
            "left": section.left_margin.cm,
            "right": section.right_margin.cm,
        }
