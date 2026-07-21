"""python-docx 共享工具函数

消除项目中重复的 docx 操作代码。
"""

from __future__ import annotations

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt

# ── 常量 ────────────────────────────────────────────────────────────

EMU_PER_CM = 360000
"""EMU (English Metric Units) 每厘米"""

EMU_PER_INCH = 914400
"""EMU 每英寸"""

ALIGN_MAP: dict[str, int] = {
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
}
"""对齐方式名称 → python-docx 枚举值映射"""


# ── 字体工具 ────────────────────────────────────────────────────────

def set_east_asian_font(run, font_name: str) -> None:
    """设置 run 的东亚字体（中文/日文/韩文）

    Args:
        run: python-docx Run 对象
        font_name: 东亚字体名称，如 "宋体"、"黑体"
    """
    rpr = run._element.get_or_add_rPr()
    rFonts = rpr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = run._element.makeelement(qn("w:rFonts"), {})
        rpr.insert(0, rFonts)
    rFonts.set(qn("w:eastAsia"), font_name)


def get_east_asian_font(font_rules: dict, language: str = "chinese", is_heading: bool = False) -> str:
    """根据语言和标题/正文类型返回合适的东亚字体名称

    Args:
        font_rules: 字体规则字典（来自 format_rules.font）
        language: 语言类型 - 'chinese' | 'japanese' | 'korean'
        is_heading: 是否为标题（标题使用不同字体）

    Returns:
        东亚字体名称
    """
    if language == "japanese":
        if is_heading:
            return font_rules.get("japanese_heading", font_rules.get("japanese", "MS Gothic"))
        return font_rules.get("japanese", "MS Mincho")
    elif language == "korean":
        if is_heading:
            return font_rules.get("korean_heading", font_rules.get("korean", "Dotum"))
        return font_rules.get("korean", "Batang")
    else:  # chinese (default)
        if is_heading:
            return font_rules.get("heading_chinese", font_rules.get("chinese", "黑体"))
        return font_rules.get("chinese", "宋体")


def set_run_font(
    run,
    en_font: str = "Times New Roman",
    cn_font: str = "宋体",
    size_pt: float | None = None,
    bold: bool = False,
) -> None:
    """统一设置 run 的字体属性

    Args:
        run: python-docx Run 对象
        en_font: 西文字体名称
        cn_font: 中文字体名称
        size_pt: 字号（磅），None 表示不设置
        bold: 是否加粗
    """
    run.font.name = en_font
    set_east_asian_font(run, cn_font)
    if size_pt is not None:
        run.font.size = Pt(size_pt)
    run.font.bold = bold


def set_paragraph_font(
    paragraph,
    en_font: str = "Times New Roman",
    cn_font: str = "宋体",
    size_pt: float | None = None,
    bold: bool = False,
) -> None:
    """批量设置段落所有 run 的字体属性

    Args:
        paragraph: python-docx Paragraph 对象
        en_font: 西文字体名称
        cn_font: 中文字体名称
        size_pt: 字号（磅），None 表示不设置
        bold: 是否加粗
    """
    for run in paragraph.runs:
        set_run_font(run, en_font, cn_font, size_pt, bold)


# ── HTML 工具 ────────────────────────────────────────────────────────

def escape_html(text: str) -> str:
    """HTML 转义（处理 &, <, >, "）

    Args:
        text: 原始文本

    Returns:
        转义后的文本
    """
    if not text:
        return ""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))
