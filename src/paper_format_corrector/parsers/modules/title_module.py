"""标题页模块：检测 TITLE, AUTHORS, AFFILIATION。"""

import re

from docx.text.paragraph import Paragraph

from ..section_types import SectionType
from .base import DetectionContext, ModuleResult, SectionModule


class TitleModule(SectionModule):
    name = "title"

    def __init__(self, config: dict):
        detect = config.get("auto_detect", {})
        self.title_pattern = re.compile(detect.get("title_pattern", r"^论文题目"))

    def detect(self, para: Paragraph, text: str, ctx: DetectionContext) -> ModuleResult | None:
        # 题目（仅第一段，未见过标题时）
        if not ctx.seen_title and self.title_pattern.match(text):
            ctx.seen_title = True
            return ModuleResult(
                label=SectionType.TITLE,
                confidence=1.0,
                reason="匹配标题模式",
            )

        # 作者行（标题之后，包含多个中文人名）
        if ctx.seen_title and not ctx.seen_abstract_cn and not ctx.seen_abstract_en:
            if self._is_author_line(text):
                return ModuleResult(
                    label=SectionType.AUTHORS,
                    confidence=0.9,
                    reason="检测到多人名分隔模式",
                )

        return None

    def _is_author_line(self, text: str) -> bool:
        if len(text) > 80:
            return False
        names = re.split(r"[,，、\s]+", text)
        if len(names) >= 2:
            cn_names = [n for n in names if re.match(r"^[一-鿿ぁ-んァ-ヶ가-힣]{2,4}$", n)]
            if len(cn_names) >= 2:
                return True
        if re.match(r"^[A-Z][a-z]+\.?\s+[A-Z][a-z]+", text):
            en_authors = re.findall(r"[A-Z][a-z]+\.?\s+[A-Z][a-z]+", text)
            if len(en_authors) >= 2:
                return True
        return False
