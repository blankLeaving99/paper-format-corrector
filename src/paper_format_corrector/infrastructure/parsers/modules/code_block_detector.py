"""代码块检测器 - 增强的代码段落检测。

检测特征:
  - 等宽字体 (Courier New / Consolas / Lucida Console 等)
  - 4空格或Tab缩进
  - 代码关键词密度 (def class if for function return import 等)
  - 无自然语言标点 (。，、)
  - 代码特征字符 ({};=<>[] 等)
"""

from __future__ import annotations

import re

from docx.text.paragraph import Paragraph

from ..section_types import SectionType
from .base import DetectionContext, ModuleResult, SectionModule


class CodeBlockDetector(SectionModule):
    """增强的代码块检测模块。"""

    name = "code_block"

    def __init__(self, config: dict):
        self._mono_fonts: set[str] = {
            "consolas", "courier new", "monospace", "fixedsys",
            "lucida console", "source code pro", "menlo", "monaco",
            "courier", "dejavu sans mono", "liberation mono",
            "noto sans mono", "fira code", "jetbrains mono",
        }
        self._code_chars: set[str] = set("{}();=<>[]|&!~^*/\\#@$")
        self._code_keywords: set[str] = {
            "def", "class", "import", "from", "return", "if", "else", "elif",
            "for", "while", "try", "except", "finally", "with", "as", "in",
            "not", "and", "or", "True", "False", "None", "self",
            "public", "private", "protected", "static", "void", "int",
            "string", "float", "double", "char", "bool", "boolean",
            "function", "var", "let", "const", "new", "this",
            "include", "define", "struct", "enum", "typedef",
            "async", "await", "yield", "lambda", "print", "echo",
            "SELECT", "FROM", "WHERE", "INSERT", "UPDATE", "DELETE",
        }
        self._cjk_punct = re.compile(r"[。，、；：！？（）【】「」『』]")

    def detect(self, para: Paragraph, text: str, ctx: DetectionContext) -> ModuleResult | None:
        if len(text) < 3:
            return None

        confidence, reason = self._check_code(para, text)
        if confidence > 0:
            return ModuleResult(
                label=SectionType.CODE,
                confidence=confidence,
                reason=reason,
            )
        return None

    def _check_code(self, para: Paragraph, text: str) -> tuple[float, str]:
        """返回 (置信度, 原因描述)"""
        # 方法1: 样式名匹配 (高置信度)
        try:
            style_name = (para.style.name or "").lower()
            if any(kw in style_name for kw in ("code", "listing", "verbatim", "program")):
                return 0.95, "样式名包含代码关键字"
        except Exception:
            pass

        # 方法2: 等宽字体 (高置信度)
        mono_confidence = self._check_mono_font_runs(para)
        if mono_confidence > 0:
            return mono_confidence, "检测到等宽字体"

        # 方法3: 缩进 + 代码特征字符
        indent_confidence = self._check_indent_and_code_chars(para, text)
        if indent_confidence > 0:
            return indent_confidence, "首行缩进+代码特征字符"

        # 方法4: 代码关键词密度
        keyword_confidence = self._check_keyword_density(text)
        if keyword_confidence > 0:
            return keyword_confidence, "代码关键词密度"

        return 0.0, ""

    def _check_mono_font_runs(self, para: Paragraph) -> float:
        """检查 runs 是否使用等宽字体。"""
        try:
            runs = para.runs
        except AttributeError:
            return 0.0
        if not runs:
            return 0.0

        mono_count = sum(
            1 for r in runs
            if (r.font.name or "").lower() in self._mono_fonts
        )
        ratio = mono_count / len(runs)

        if ratio >= 0.9:
            return 0.95
        if ratio >= 0.7:
            return 0.90
        if mono_count > 0 and ratio >= 0.5:
            return 0.85
        return 0.0

    def _check_indent_and_code_chars(self, para: Paragraph, text: str) -> float:
        """检查首行缩进 + 代码特征字符。"""
        try:
            raw_text = para.text
        except AttributeError:
            raw_text = text

        if not raw_text.startswith(("    ", "\t")):
            return 0.0

        code_char_count = sum(1 for c in text if c in self._code_chars)
        if code_char_count >= 3:
            return 0.85
        if code_char_count >= 2:
            return 0.75
        return 0.0

    def _check_keyword_density(self, text: str) -> float:
        """检查代码关键词密度（无中文标点时）。"""
        if self._cjk_punct.search(text):
            return 0.0
        if len(text) > 300:
            return 0.0

        words = set(re.findall(r"\b[a-zA-Z_]\w*\b", text))
        keyword_hits = words & self._code_keywords
        code_char_count = sum(1 for c in text if c in self._code_chars)

        if len(keyword_hits) >= 3 and code_char_count >= 2:
            return 0.80
        if len(keyword_hits) >= 2 and code_char_count >= 1:
            return 0.70
        return 0.0
