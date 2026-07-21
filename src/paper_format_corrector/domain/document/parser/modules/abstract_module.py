"""摘要模块：检测 ABSTRACT_CN/EN, KEYWORDS_CN/EN。"""

import re

from docx.text.paragraph import Paragraph

from ..section_types import SectionType
from .base import DetectionContext, ModuleResult, SectionModule


class AbstractModule(SectionModule):
    name = "abstract"

    def __init__(self, config: dict):
        detect = config.get("auto_detect", {})
        self.abstract_pattern = re.compile(
            detect.get("abstract_pattern", r"^摘\s*要$|^Abstract$|^ABSTRACT$")
        )
        self.abstract_en_pattern = re.compile(
            detect.get("abstract_en_pattern", r"^Abstract$|^ABSTRACT$")
        )
        self.keywords_pattern = re.compile(
            detect.get("keywords_pattern", r"^关键词[:：]|^Key\s*[Ww]ords[:：]?")
        )

    def detect(self, para: Paragraph, text: str, ctx: DetectionContext) -> ModuleResult | None:
        # 摘要
        if self.abstract_pattern.match(text):
            if self.abstract_en_pattern.match(text):
                ctx.seen_abstract_en = True
                return ModuleResult(label=SectionType.ABSTRACT_EN, reason="匹配英文摘要模式")
            ctx.seen_abstract_cn = True
            return ModuleResult(label=SectionType.ABSTRACT_CN, reason="匹配中文摘要模式")

        # 关键词
        if self.keywords_pattern.match(text):
            is_en = bool(re.search(r"[Kk]ey\s*[Ww]ords", text))
            label = SectionType.KEYWORDS_EN if is_en else SectionType.KEYWORDS_CN
            return ModuleResult(label=label, reason="匹配关键词模式")

        return None
