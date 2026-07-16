"""离线规则化需求解析器

基于正则表达式和规则匹配，从需求文档中提取格式规则。
无需 LLM API，完全离线运行。

支持的输入格式：
- 中文自然语言描述（如"正文用宋体小四"）
- 表格格式的需求文档
- Markdown 格式的需求文档
- 混合格式

示例输入：
    正文：宋体，小四号字，1.5倍行距，首行缩进2字符
    一级标题：黑体，三号字，居中，加粗
    页边距：上下2.54cm，左右3.17cm
"""

import re
from typing import Any


# 中文字号到 pt 的映射
# 注意：必须先列出"小X"再列出"X号"，避免正则匹配时顺序错误
CHINESE_SIZE_MAP: dict[str, float] = {
    "小初": 36, "初号": 42,
    "小一": 24, "一号": 26,
    "小二": 18, "二号": 22,
    "小三": 15, "三号": 16,
    "小四": 12, "四号": 14,
    "小五": 9, "五号": 10.5,
}

# 字体名称模式（中文名 -> 正则模式）
FONT_PATTERNS: dict[str, str] = {
    "宋体": r"宋体|SimSun|songti",
    "黑体": r"黑体|SimHei|heiti",
    "楷体": r"楷体|KaiTi|kaiti",
    "仿宋": r"仿宋|FangSong|fangsong",
    "Times New Roman": r"Times\s*New\s*Roman|TNR|times\s*new\s*roman",
    "Arial": r"Arial|arial",
    "Calibri": r"Calibri|calibri",
    "Helvetica": r"Helvetica|helvetica",
}

# 对齐方式映射
ALIGNMENT_MAP: dict[str, str] = {
    "居中": "center", "左对齐": "left", "左": "left",
    "右对齐": "right", "右": "right", "两端对齐": "justify",
    "分散对齐": "distribute", "center": "center", "left": "left",
    "right": "right", "justify": "justify",
}

# 行距类型映射
LINE_SPACING_MAP: dict[str, dict[str, Any]] = {
    "单倍行距": {"type": "single", "value": 1.0},
    "1.0倍行距": {"type": "single", "value": 1.0},
    "1.5倍行距": {"type": "multiple", "value": 1.5},
    "双倍行距": {"type": "multiple", "value": 2.0},
    "2.0倍行距": {"type": "multiple", "value": 2.0},
    "多倍行距": {"type": "multiple", "value": 1.5},  # 默认1.5
}


class RuleParser:
    """规则化需求解析器（离线版）

    从自然语言或结构化文本中提取格式规则，返回标准配置字典。
    无需外部 LLM API，完全离线运行。
    """

    def __init__(self):
        self._compiled_patterns = {}

    def parse(self, text: str) -> dict[str, Any]:
        """解析需求文本，返回配置字典

        Args:
            text: 需求文档文本内容

        Returns:
            标准格式配置字典
        """
        config: dict[str, Any] = {"format_rules": {}}

        # 按行处理
        lines = text.split("\n")
        context = "unknown"  # 当前上下文（正文、标题等）

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测上下文切换
            new_context = self._detect_context(line)
            if new_context:
                context = new_context

            # 提取各类规则
            self._extract_font_rules(line, config, context)
            self._extract_size_rules(line, config, context)
            self._extract_alignment_rules(line, config, context)
            self._extract_spacing_rules(line, config, context)
            self._extract_indent_rules(line, config, context)
            self._extract_margin_rules(line, config)
            self._extract_bold_rules(line, config, context)

        return config

    def _detect_context(self, line: str) -> str | None:
        """检测当前行的上下文类型"""
        context_patterns = {
            "heading1": r"一级标题|章标题|chapter\s*1|heading\s*1",
            "heading2": r"二级标题|节标题|chapter\s*2|heading\s*2",
            "heading3": r"三级标题|小节标题|chapter\s*3|heading\s*3",
            "body": r"正文|body|main\s*text",
            "abstract": r"摘要|abstract",
            "keywords": r"关键词|keywords",
            "references": r"参考文献|references",
            "title": r"题目|论文题目|title",
        }

        for ctx, pattern in context_patterns.items():
            if re.search(pattern, line, re.IGNORECASE):
                return ctx
        return None

    def _get_section_config(self, config: dict, context: str) -> dict:
        """获取指定上下文的配置节"""
        rules = config.setdefault("format_rules", {})

        if context in ("heading1", "heading2", "heading3"):
            headings = rules.setdefault("headings", {})
            return headings.setdefault(context, {})
        elif context == "body":
            return rules.setdefault("body_text", {})
        elif context == "abstract":
            return rules.setdefault("abstract", {})
        elif context == "keywords":
            return rules.setdefault("keywords", {})
        elif context == "references":
            return rules.setdefault("references", {})
        elif context == "title":
            return rules.setdefault("title_page", {})
        else:
            # 默认放到 body_text
            return rules.setdefault("body_text", {})

    def _extract_font_rules(self, line: str, config: dict, context: str) -> None:
        """提取字体规则"""
        # 匹配中文字体
        for font_name, pattern in FONT_PATTERNS.items():
            if re.search(pattern, line, re.IGNORECASE):
                section = self._get_section_config(config, context)
                if context.startswith("heading"):
                    section["chinese_font"] = font_name
                elif context == "body":
                    if font_name in ("宋体", "黑体", "楷体", "仿宋"):
                        section["chinese_font"] = font_name
                    else:
                        section["english_font"] = font_name
                else:
                    section["font"] = font_name

    def _extract_size_rules(self, line: str, config: dict, context: str) -> None:
        """提取字号规则"""
        # 匹配中文字号（如"小四号字"、"三号"）
        # 注意：必须先匹配"小X"再匹配"X号"，避免"小四"被错误匹配为"四号"
        for cn_size, pt_size in CHINESE_SIZE_MAP.items():
            if re.search(rf"{cn_size}\s*号?", line):
                section = self._get_section_config(config, context)
                section["font_size"] = pt_size
                return

        # 匹配 pt 值（如"12pt"、"12磅"、"12点"）
        pt_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:pt|磅|点)", line, re.IGNORECASE)
        if pt_match:
            section = self._get_section_config(config, context)
            section["font_size"] = float(pt_match.group(1))
            return

        # 匹配纯数字（如"字号12"）
        size_match = re.search(r"字号\s*[:：]?\s*(\d+(?:\.\d+)?)", line)
        if size_match:
            section = self._get_section_config(config, context)
            section["font_size"] = float(size_match.group(1))

    def _extract_alignment_rules(self, line: str, config: dict, context: str) -> None:
        """提取对齐方式规则"""
        for cn_name, en_name in ALIGNMENT_MAP.items():
            if cn_name in line:
                section = self._get_section_config(config, context)
                section["align"] = en_name
                return

    def _extract_spacing_rules(self, line: str, config: dict, context: str) -> None:
        """提取行距规则"""
        # 匹配倍数行距（如"1.5倍行距"）
        multiple_match = re.search(r"(\d+(?:\.\d+)?)\s*倍行距", line)
        if multiple_match:
            value = float(multiple_match.group(1))
            section = self._get_section_config(config, context)
            section["line_spacing"] = value
            return

        # 匹配英文行距模式（如"1.5 line spacing"）
        en_multiple_match = re.search(r"(\d+(?:\.\d+)?)\s*line\s*spacing", line, re.IGNORECASE)
        if en_multiple_match:
            value = float(en_multiple_match.group(1))
            section = self._get_section_config(config, context)
            section["line_spacing"] = value
            return

        # 匹配固定行距（如"固定值20磅"）
        exact_match = re.search(r"固定值\s*(\d+(?:\.\d+)?)\s*(?:磅|pt)", line)
        if exact_match:
            value = float(exact_match.group(1))
            section = self._get_section_config(config, context)
            section["line_spacing"] = {"type": "exact", "value": value}
            return

        # 匹配预设行距名称
        for cn_name, spacing_info in LINE_SPACING_MAP.items():
            if cn_name in line:
                section = self._get_section_config(config, context)
                section["line_spacing"] = spacing_info["value"]
                return

    def _extract_indent_rules(self, line: str, config: dict, context: str) -> None:
        """提取缩进规则"""
        # 首行缩进（如"首行缩进2字符"）
        indent_match = re.search(r"首行缩进\s*(\d+(?:\.\d+)?)\s*字符", line)
        if indent_match:
            value = float(indent_match.group(1))
            section = self._get_section_config(config, context)
            section["first_line_indent"] = value
            return

        # 左缩进（如"左缩进2cm"）
        left_indent_match = re.search(r"左缩进\s*(\d+(?:\.\d+)?)\s*(?:cm|厘米)", line)
        if left_indent_match:
            value = float(left_indent_match.group(1))
            section = self._get_section_config(config, context)
            section["left_indent"] = value
            return

        # 不缩进
        if re.search(r"不缩进|无缩进|零缩进", line):
            section = self._get_section_config(config, context)
            section["first_line_indent"] = 0

    def _extract_margin_rules(self, line: str, config: dict) -> None:
        """提取页边距规则"""
        margins: dict[str, float] = {}

        # 匹配"上下Xcm，左右Ycm"
        tl_match = re.search(r"上下?\s*(\d+(?:\.\d+)?)\s*(?:cm|厘米)", line)
        lr_match = re.search(r"左右?\s*(\d+(?:\.\d+)?)\s*(?:cm|厘米)", line)
        if tl_match and lr_match:
            value = float(tl_match.group(1))
            lr_value = float(lr_match.group(1))
            margins = {"top": value, "bottom": value, "left": lr_value, "right": lr_value}
        else:
            # 匹配单独的边距
            top_match = re.search(r"上边距\s*(\d+(?:\.\d+)?)\s*(?:cm|厘米)", line)
            bottom_match = re.search(r"下边距\s*(\d+(?:\.\d+)?)\s*(?:cm|厘米)", line)
            left_match = re.search(r"左边距\s*(\d+(?:\.\d+)?)\s*(?:cm|厘米)", line)
            right_match = re.search(r"右边距\s*(\d+(?:\.\d+)?)\s*(?:cm|厘米)", line)

            if top_match:
                margins["top"] = float(top_match.group(1))
            if bottom_match:
                margins["bottom"] = float(bottom_match.group(1))
            if left_match:
                margins["left"] = float(left_match.group(1))
            if right_match:
                margins["right"] = float(right_match.group(1))

        if margins:
            config.setdefault("format_rules", {})["margins"] = margins

    def _extract_bold_rules(self, line: str, config: dict, context: str) -> None:
        """提取加粗规则"""
        if re.search(r"加粗|粗体|bold", line, re.IGNORECASE):
            section = self._get_section_config(config, context)
            section["bold"] = True
        elif re.search(r"不加粗|非粗体|regular", line, re.IGNORECASE):
            section = self._get_section_config(config, context)
            section["bold"] = False


def parse_requirement_text(text: str) -> dict[str, Any]:
    """便捷函数：解析需求文本

    Args:
        text: 需求文档文本内容

    Returns:
        标准格式配置字典
    """
    parser = RuleParser()
    return parser.parse(text)


def parse_requirement_file(file_path: str) -> dict[str, Any]:
    """便捷函数：解析需求文件

    Args:
        file_path: 需求文件路径（支持 .txt, .md, .yaml, .yml）

    Returns:
        标准格式配置字典
    """
    from pathlib import Path

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"需求文件不存在: {file_path}")

    text = path.read_text(encoding="utf-8")
    return parse_requirement_text(text)
