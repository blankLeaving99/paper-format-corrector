"""参考文献模块：检测 REFERENCE_TITLE, REFERENCE_ITEM。"""

import re

from docx.text.paragraph import Paragraph

from ..section_types import SectionType
from .base import DetectionContext, ModuleResult, SectionModule


class ReferenceModule(SectionModule):
    name = "reference"

    def __init__(self, config: dict):
        detect = config.get("auto_detect", {})
        self.ref_keywords = detect.get("reference_keywords", ["参考文献"])

    def detect(self, para: Paragraph, text: str, ctx: DetectionContext) -> ModuleResult | None:
        # 在参考文献区域内
        if ctx.in_references:
            if self._is_reference_item(text):
                return ModuleResult(label=SectionType.REFERENCE_ITEM, reason="参考文献条目")
            else:
                ctx.in_references = False
                return None

        # 参考文献标题
        if text in self.ref_keywords or any(text.startswith(kw) for kw in self.ref_keywords):
            ctx.in_references = True
            return ModuleResult(label=SectionType.REFERENCE_TITLE, reason="匹配参考文献标题关键词")

        return None

    def validate(
        self,
        paragraphs: list[Paragraph],
        labels: list[SectionType],
        ctx: DetectionContext,
    ) -> list[dict]:
        """校验参考文献条目格式。"""
        corrections = []
        for i, (label, para) in enumerate(zip(labels, paragraphs)):
            if label == SectionType.REFERENCE_ITEM:
                text = para.text.strip()
                if not self._is_reference_item(text):
                    corrections.append({
                        "index": i,
                        "from": label,
                        "to": SectionType.BODY,
                        "reason": "参考文献区域内但不匹配引用格式",
                    })
        return corrections

    @staticmethod
    def _is_reference_item(text: str) -> bool:
        if re.match(r"^\[\d+\]", text):
            return True
        if re.match(r"^\d+[\.\)]\s", text):
            return True
        if re.match(r"^[A-Z][a-z]+,?\s+[A-Z]\.", text) and re.search(r"\(\d{4}\)", text):
            return True
        return False
