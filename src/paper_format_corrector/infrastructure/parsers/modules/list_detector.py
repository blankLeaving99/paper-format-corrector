"""列表检测器 - 检测有序/无序列表及其层级。

检测特征:
  - 有序列表: '1.', '1)', 'a.', 'a)', '(1)'
  - 无序列表: '•', '-', '*', '·', '◦'
  - 多级列表: 检测缩进层级 (每级约 0.5 inch / 1.27 cm)
"""

from __future__ import annotations

import re

from docx.shared import Emu
from docx.text.paragraph import Paragraph

from ..section_types import SectionType
from .base import DetectionContext, ModuleResult, SectionModule

# 有序列表前缀正则
_ORDERED_PATTERNS = [
    re.compile(r"^(\d{1,3})[.\)]\s"),           # 1. 2) 3.
    re.compile(r"^\((\d{1,3})\)\s"),             # (1) (2)
    re.compile(r"^([a-z])[.\)]\s", re.IGNORECASE),  # a. b) c.
    re.compile(r"^\(([a-z])\)\s", re.IGNORECASE),   # (a) (b)
    re.compile(r"^([IVXLCDM]+)[.\)]\s"),          # I. II) III.
]

# 无序列表前缀正则
_UNORDERED_MARKERS = {"•", "◦", "‣", "⁃", "·"}


class ListDetector(SectionModule):
    """列表检测模块。"""

    name = "list"

    def __init__(self, config: dict):
        detect = config.get("auto_detect", {})
        self._min_indent_inches = detect.get("list_min_indent_inches", 0.2)
        self._list_style_keywords = {"list", "bullet", "number", "toc"}
        # 每级缩进约 0.5 inch (12.7mm)
        self._indent_step_inches = 0.5

    def detect(self, para: Paragraph, text: str, ctx: DetectionContext) -> ModuleResult | None:
        if len(text) < 2:
            return None

        # 检查样式名
        style_conf = self._check_list_style(para)
        if style_conf > 0:
            label = SectionType.BODY  # 列表项在格式化时按正文处理，但标记类型
            return ModuleResult(
                label=label,
                confidence=style_conf,
                reason="段落样式包含列表关键字",
                extras={"list_type": "ordered", "level": 0},
            )

        # 检测无序列表
        unordered = self._check_unordered(text)
        if unordered:
            level = self._detect_indent_level(para)
            return ModuleResult(
                label=SectionType.BODY,
                confidence=0.88,
                reason=f"无序列表标记: '{unordered}'",
                extras={"list_type": "unordered", "level": level, "marker": unordered},
            )

        # 检测有序列表
        ordered = self._check_ordered(text)
        if ordered:
            level = self._detect_indent_level(para)
            return ModuleResult(
                label=SectionType.BODY,
                confidence=0.90,
                reason=f"有序列表前缀: '{ordered}'",
                extras={"list_type": "ordered", "level": level, "number": ordered},
            )

        return None

    def _check_list_style(self, para: Paragraph) -> float:
        """检查 Word 样式名是否包含列表关键字。"""
        try:
            style_name = (para.style.name or "").lower()
        except Exception:
            return 0.0

        if any(kw in style_name for kw in self._list_style_keywords):
            return 0.95
        return 0.0

    def _check_unordered(self, text: str) -> str | None:
        """检测无序列表标记，返回标记字符或 None。"""
        first_char = text[0]
        if first_char in _UNORDERED_MARKERS:
            return first_char

        # 检查 "-" 或 "*" 开头 (后面跟空格)
        if first_char in ("-", "*") and len(text) > 1 and text[1] == " ":
            return first_char

        return None

    def _check_ordered(self, text: str) -> str | None:
        """检测有序列表前缀，返回数字/字母或 None。"""
        for pattern in _ORDERED_PATTERNS:
            m = pattern.match(text)
            if m:
                return m.group(1)
        return None

    def _detect_indent_level(self, para: Paragraph) -> int:
        """检测段落缩进层级 (0-based)。"""
        try:
            # python-docx: paragraph.paragraph_format.first_line_indent
            # 或 paragraph.paragraph_format.left_indent
            pf = para.paragraph_format
            indent = pf.first_line_indent or pf.left_indent
            if indent is None:
                return 0
            # 转换为 inches
            if isinstance(indent, Emu):
                inches = indent / 914400.0
            elif isinstance(indent, (int, float)):
                inches = indent
            else:
                return 0
            level = int(inches / self._indent_step_inches)
            return max(0, min(level, 5))
        except Exception:
            return 0
