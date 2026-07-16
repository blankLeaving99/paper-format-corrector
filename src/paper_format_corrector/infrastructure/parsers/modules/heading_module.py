"""标题层级模块：检测 CHAPTER, SECTION, SUBSECTION。"""

import re

from docx.text.paragraph import Paragraph

from ..section_types import SectionType
from .base import DetectionContext, ModuleResult, SectionModule


class HeadingModule(SectionModule):
    name = "heading"

    def __init__(self, config: dict):
        detect = config.get("auto_detect", {})
        self.chapter_pattern = re.compile(
            detect.get("chapter_pattern", r"^第[一二三四五六七八九十百零\d]+[章部分篇]")
        )
        self.section_pattern = re.compile(
            detect.get("section_pattern", r"^\d+\.\d+")
        )
        self.subsection_pattern = re.compile(
            detect.get("subsection_pattern", r"^\d+\.\d+\.\d+")
        )
        self._mono_fonts = {
            "consolas", "courier new", "monospace", "fixedsys",
            "lucida console", "source code pro", "menlo", "monaco",
        }

    def detect(self, para: Paragraph, text: str, ctx: DetectionContext) -> ModuleResult | None:
        # 小节标题 (x.x.x) — 必须在节标题之前检测
        if self.subsection_pattern.match(text):
            return ModuleResult(label=SectionType.SUBSECTION, reason="匹配小节标题模式（x.x.x）")

        # 节标题 (x.x)
        if self.section_pattern.match(text):
            return ModuleResult(label=SectionType.SECTION, reason="匹配节标题模式（x.x）")

        # 章标题（第X章）
        if self.chapter_pattern.match(text):
            ctx.chapter_count += 1
            return ModuleResult(
                label=SectionType.CHAPTER,
                extras={"chapter_num": ctx.chapter_count},
                reason="匹配章标题模式（第X章）",
            )

        # 启发式标题检测（字体属性）
        result = self._heuristic_heading(para, text, ctx)
        if result is not None:
            return result

        return None

    def _heuristic_heading(self, para: Paragraph, text: str, ctx: DetectionContext) -> ModuleResult | None:
        """根据字体属性推断疑似标题。"""
        if len(text) > 80:
            return None
        try:
            runs = para.runs
        except AttributeError:
            return None
        if not runs:
            return None

        first_run = runs[0]
        try:
            is_bold = first_run.font.bold
            font_size = first_run.font.size
            font_size_pt = font_size.pt if font_size else None
        except Exception:
            return None

        if not is_bold:
            return None

        try:
            is_centered = (para.alignment == 1)
        except Exception:
            is_centered = False

        # 章标题：加粗 + 居中 + 大字号 (>= 14pt)
        if is_centered and font_size_pt and font_size_pt >= 14:
            if not re.match(r"^[\d\s\.\-\(\)]+$", text):
                ctx.chapter_count += 1
                return ModuleResult(
                    label=SectionType.CHAPTER,
                    extras={"chapter_num": ctx.chapter_count},
                    confidence=0.8,
                    reason="启发式：加粗+居中+大字号",
                )

        # 节标题：加粗 + 大字号 (>= 13pt) + 短文本
        if font_size_pt and font_size_pt >= 13 and len(text) < 50:
            return ModuleResult(
                label=SectionType.SECTION,
                confidence=0.7,
                reason="启发式：加粗+大字号",
            )

        return None
