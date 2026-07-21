"""图表标题模块：检测 FIGURE_CAPTION, TABLE_CAPTION。

支持多种中英文图表标题格式：
- 中文：图 1、图1-1、图 1.1、图1 xxx
- 英文：Fig. 1、Fig 1、Figure 1、Figure 1-1、Fig.1 xxx
- 中文：表 1、表1-1、表 1.1、表1 xxx
- 英文：Table 1、TABLE 1、Table 1-1、Table1 xxx
"""

import re

from docx.text.paragraph import Paragraph

from ..section_types import SectionType
from .base import DetectionContext, ModuleResult, SectionModule


class CaptionModule(SectionModule):
    name = "caption"

    def __init__(self, config: dict):
        detect = config.get("auto_detect", {})
        # 扩展的图标题正则：支持 中文图、Fig.、Figure 等格式
        fig_pattern = detect.get(
            "figure_caption_pattern",
            r"^(图\s*\d|Fig\.?\s*\d|Figure\s*\d|图\s*[\d一二三四五六七八九十]+)",
        )
        self.fig_caption_pattern = re.compile(fig_pattern, re.IGNORECASE)
        # 扩展的表标题正则：支持 中文表、Table、TABLE 等格式
        tab_pattern = detect.get(
            "table_caption_pattern",
            r"^(表\s*\d|Table\s*\d|TABLE\s*\d|表\s*[\d一二三四五六七八九十]+)",
        )
        self.tab_caption_pattern = re.compile(tab_pattern, re.IGNORECASE)

    def detect(self, para: Paragraph, text: str, ctx: DetectionContext) -> ModuleResult | None:
        # 图标题
        if self.fig_caption_pattern.match(text):
            num = self._parse_caption_num(text, "图")
            if not num:
                num = self._parse_caption_num_en(text)
            return ModuleResult(
                label=SectionType.FIGURE_CAPTION,
                extras=num,
                reason="匹配图注模式",
            )

        # 表标题
        if self.tab_caption_pattern.match(text):
            num = self._parse_caption_num(text, "表")
            if not num:
                num = self._parse_caption_num_en(text, prefixes=("Table", "TABLE"))
            return ModuleResult(
                label=SectionType.TABLE_CAPTION,
                extras=num,
                reason="匹配表注模式",
            )

        return None

    @staticmethod
    def _parse_caption_num(text: str, prefix: str) -> dict:
        """解析中文编号，如 '图1-2 xxx' -> {'num': '1-2'}"""
        escaped = re.escape(prefix)
        m = re.match(rf"^{escaped}\.?\s*(\d+[\-\.]\d+|\d+)", text, re.IGNORECASE)
        if m:
            return {"num": m.group(1)}
        return {}

    @staticmethod
    def _parse_caption_num_en(text: str, prefixes: tuple[str, ...] = ("Fig.", "Fig", "Figure")) -> dict:
        """解析英文编号，如 'Fig. 1-2 xxx' -> {'num': '1-2'}"""
        for prefix in prefixes:
            escaped = re.escape(prefix)
            m = re.match(rf"^{escaped}\.?\s*(\d+[\-\.]\d+|\d+)", text, re.IGNORECASE)
            if m:
                return {"num": m.group(1)}
        return {}
