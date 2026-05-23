from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


class TOCHandler:
    """目录处理器"""

    def __init__(self, config):
        toc_config = config.get("format_rules", {}).get("toc", {})
        self.enabled = toc_config.get("enabled", True)
        self.title = toc_config.get("title", "目  录")
        self.title_font_size = toc_config.get("title_font_size", 16)
        self.title_bold = toc_config.get("title_bold", True)
        self.title_align = toc_config.get("title_align", "center")
        self.max_level = toc_config.get("max_level", 3)
        self.font_size = toc_config.get("font_size", 12)
        self.line_spacing = toc_config.get("line_spacing", 1.5)
        self.font_rules = config.get("format_rules", {}).get("font", {})

    def insert_toc(self, doc, position=0):
        """在指定位置插入目录"""
        if not self.enabled:
            return

        # 在文档开头插入目录标题和 TOC 字段
        # python-docx 不直接支持在指定位置插入，需要通过 XML 操作
        body = doc.element.body

        # 创建目录标题段落
        title_elem = self._create_toc_title()

        # 创建 TOC 字段
        toc_elem = self._create_toc_field()

        # 插入到文档开头（在第一个子元素之前）
        first_child = body[0] if len(body) > 0 else None
        if first_child is not None:
            first_child.addprevious(title_elem)
            first_child.addprevious(toc_elem)
        else:
            body.append(title_elem)
            body.append(toc_elem)

    def _create_toc_title(self):
        """创建目录标题段落 XML"""
        p = OxmlElement("w:p")

        # 段落属性
        pPr = OxmlElement("w:pPr")
        jc = OxmlElement("w:jc")
        jc.set(qn("w:val"), self.title_align)
        pPr.append(jc)

        # 段前段后
        spacing = OxmlElement("w:spacing")
        spacing.set(qn("w:before"), "240")
        spacing.set(qn("w:after"), "120")
        pPr.append(spacing)

        p.append(pPr)

        # 运行
        r = OxmlElement("w:r")
        rPr = OxmlElement("w:rPr")

        # 字体
        rFonts = OxmlElement("w:rFonts")
        rFonts.set(qn("w:ascii"), self.font_rules.get("english", "Times New Roman"))
        rFonts.set(qn("w:eastAsia"), self.font_rules.get("heading_chinese", "黑体"))
        rPr.append(rFonts)

        # 字号
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), str(int(self.title_font_size * 2)))
        rPr.append(sz)
        szCs = OxmlElement("w:szCs")
        szCs.set(qn("w:val"), str(int(self.title_font_size * 2)))
        rPr.append(szCs)

        # 加粗
        if self.title_bold:
            b = OxmlElement("w:b")
            rPr.append(b)

        r.append(rPr)

        t = OxmlElement("w:t")
        t.text = self.title
        r.append(t)
        p.append(r)

        return p

    def _create_toc_field(self):
        """创建 TOC 字段 XML"""
        p = OxmlElement("w:p")

        # 开始字段
        r1 = OxmlElement("w:r")
        fldChar1 = OxmlElement("w:fldChar")
        fldChar1.set(qn("w:fldCharType"), "begin")
        r1.append(fldChar1)
        p.append(r1)

        # 字段指令
        r2 = OxmlElement("w:r")
        instrText = OxmlElement("w:instrText")
        instrText.set(qn("xml:space"), "preserve")
        instrText.text = f' TOC \\o "1-{self.max_level}" \\h \\z \\u '
        r2.append(instrText)
        p.append(r2)

        # 分隔字段
        r3 = OxmlElement("w:r")
        fldChar2 = OxmlElement("w:fldChar")
        fldChar2.set(qn("w:fldCharType"), "separate")
        r3.append(fldChar2)
        p.append(r3)

        # 占位文本
        r4 = OxmlElement("w:r")
        rPr4 = OxmlElement("w:rPr")
        color = OxmlElement("w:color")
        color.set(qn("w:val"), "808080")
        rPr4.append(color)
        r4.append(rPr4)
        t = OxmlElement("w:t")
        t.text = '(请在 Word 中右键点击此处，选择"更新域"以生成目录)'
        r4.append(t)
        p.append(r4)

        # 结束字段
        r5 = OxmlElement("w:r")
        fldChar3 = OxmlElement("w:fldChar")
        fldChar3.set(qn("w:fldCharType"), "end")
        r5.append(fldChar3)
        p.append(r5)

        return p

    def has_toc(self, doc):
        """检查文档是否已有目录"""
        for para in doc.paragraphs:
            text = para.text.strip()
            if text == self.title or text in ("目录", "目 录", "目  录"):
                return True
        # 检查是否有 TOC 字段
        for field in doc.element.findall(".//" + qn("w:instrText")):
            if field.text and "TOC" in field.text:
                return True
        return False
