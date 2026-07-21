"""脚注/尾注检测器 - 检测脚注和尾注段落。

检测特征:
  - 上标数字 (¹²³⁴⁵⁶⁷⁸⁹⁰)
  - 脚注分隔线 (─────────)
  - 字号偏小 (8pt/9pt)
  - 段落首行缩进
  - 以上标标记开头的段落
"""

from __future__ import annotations

import re

from docx.text.paragraph import Paragraph

from ..section_types import SectionType
from .base import DetectionContext, ModuleResult, SectionModule

# 上标数字字符
_SUPERSCRIPT_DIGITS = set("⁰¹²³⁴⁵⁶⁷⁸⁹⁰")
_SUPERSCRIPT_PATTERN = re.compile(r"^[⁰¹²³⁴⁵⁶⁷⁸⁹⁰]+[.\s]")

# 脚注分隔线模式
_FOOTNOTE_SEPARATOR = re.compile(r"^[─━\-]{3,}$")

# 脚注编号模式 (上标数字 + 内容)
_FOOTNOTE_REF_PATTERN = re.compile(r"^(\d{1,3})[.\s]")


class FootnoteDetector(SectionModule):
    """脚注/尾注检测模块。"""

    name = "footnote"

    def __init__(self, config: dict):
        detect = config.get("auto_detect", {})
        self._footnote_font_size_pt: float = detect.get("footnote_font_size_pt", 9.0)
        self._footnote_max_ratio: float = detect.get("footnote_font_ratio", 0.85)
        self._body_font_size_pt: float = detect.get("body_font_size_pt", 12.0)

    def detect(self, para: Paragraph, text: str, ctx: DetectionContext) -> ModuleResult | None:
        if not text:
            return None

        # 方法1: 脚注分隔线
        if _FOOTNOTE_SEPARATOR.match(text):
            return ModuleResult(
                label=SectionType.FOOTNOTE,
                confidence=0.95,
                reason="检测到脚注分隔线",
            )

        # 方法2: 以上标数字开头
        if _SUPERSCRIPT_PATTERN.match(text):
            return ModuleResult(
                label=SectionType.FOOTNOTE,
                confidence=0.92,
                reason="以上标数字标记开头",
            )

        # 方法3: 字号偏小 (< body_font_size * ratio)
        font_conf = self._check_small_font(para)
        if font_conf > 0:
            # 进一步判断是脚注还是尾注
            note_type = self._distinguish_footnote_endnote(para)
            return ModuleResult(
                label=note_type,
                confidence=font_conf,
                reason="字号偏小，疑似脚注/尾注",
            )

        # 方法4: 短段落 + 首行缩进 + 以数字编号开头
        short_conf = self._check_short_numbered(para, text)
        if short_conf > 0:
            return ModuleResult(
                label=SectionType.FOOTNOTE,
                confidence=short_conf,
                reason="短段落+首行缩进+数字编号",
            )

        return None

    def _check_small_font(self, para: Paragraph) -> float:
        """检查字号是否偏小。"""
        try:
            runs = para.runs
        except AttributeError:
            return 0.0
        if not runs:
            return 0.0

        small_count = 0
        total_with_size = 0

        for run in runs:
            try:
                font_size = run.font.size
                if font_size is None:
                    continue
                total_with_size += 1
                size_pt = font_size.pt if hasattr(font_size, "pt") else font_size / 12700.0
                if size_pt <= self._footnote_font_size_pt:
                    small_count += 1
            except Exception:
                continue

        if total_with_size == 0:
            return 0.0

        ratio = small_count / total_with_size
        if ratio >= 0.8:
            return 0.85
        if ratio >= 0.6:
            return 0.75
        return 0.0

    def _distinguish_footnote_endnote(self, para: Paragraph) -> SectionType:
        """区分脚注和尾注。"""
        # 简单策略: 检查段落位置或样式名
        try:
            style_name = (para.style.name or "").lower()
        except Exception:
            style_name = ""

        if "endnote" in style_name or "尾注" in style_name:
            return SectionType.ENDNOTE
        if "footnote" in style_name or "脚注" in style_name:
            return SectionType.FOOTNOTE

        # 默认归为脚注 (更常见)
        return SectionType.FOOTNOTE

    def _check_short_numbered(self, para: Paragraph, text: str) -> float:
        """检查短段落 + 首行缩进 + 数字编号。"""
        if len(text) > 150:
            return 0.0

        # 以数字编号开头
        m = _FOOTNOTE_REF_PATTERN.match(text)
        if not m:
            return 0.0

        # 检查首行缩进
        try:
            pf = para.paragraph_format
            indent = pf.first_line_indent
            if indent is not None:
                indent_pt = indent.pt if hasattr(indent, "pt") else indent / 12700.0
                if indent_pt > 0:
                    return 0.70
        except Exception:
            pass

        return 0.0
