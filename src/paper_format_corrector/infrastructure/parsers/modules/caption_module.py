"""图表标题模块：检测 FIGURE_CAPTION, TABLE_CAPTION。"""

import re

from docx.text.paragraph import Paragraph

from ..section_types import SectionType
from .base import DetectionContext, ModuleResult, SectionModule


class CaptionModule(SectionModule):
    name = "caption"

    def __init__(self, config: dict):
        detect = config.get("auto_detect", {})
        self.fig_caption_pattern = re.compile(
            detect.get("figure_caption_pattern", r"^图\s*\d")
        )
        self.tab_caption_pattern = re.compile(
            detect.get("table_caption_pattern", r"^表\s*\d")
        )

    def detect(self, para: Paragraph, text: str, ctx: DetectionContext) -> ModuleResult | None:
        # 图标题
        if self.fig_caption_pattern.match(text):
            return ModuleResult(
                label=SectionType.FIGURE_CAPTION,
                extras=self._parse_caption_num(text, "图"),
                reason="匹配图注模式（图X）",
            )

        # 表标题
        if self.tab_caption_pattern.match(text):
            return ModuleResult(
                label=SectionType.TABLE_CAPTION,
                extras=self._parse_caption_num(text, "表"),
                reason="匹配表注模式（表X）",
            )

        return None

    @staticmethod
    def _parse_caption_num(text: str, prefix: str) -> dict:
        escaped = re.escape(prefix)
        m = re.match(rf"^{escaped}\.?\s*(\d+[\-\.]\d+|\d+)", text, re.IGNORECASE)
        if m:
            return {"num": m.group(1)}
        return {}
