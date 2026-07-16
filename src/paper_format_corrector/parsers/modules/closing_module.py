"""结尾模块：检测 ACKNOWLEDGMENT_TITLE, APPENDIX_TITLE, TOC_TITLE。"""

import re

from docx.text.paragraph import Paragraph

from ..section_types import SectionType
from .base import DetectionContext, ModuleResult, SectionModule


class ClosingModule(SectionModule):
    name = "closing"

    def __init__(self, config: dict):
        detect = config.get("auto_detect", {})
        self.ack_pattern = re.compile(
            detect.get("acknowledgment_pattern", r"^致\s*谢$")
        )
        self.appendix_pattern = re.compile(
            detect.get("appendix_pattern", r"^附\s*录[A-Z]?")
        )

    def detect(self, para: Paragraph, text: str, ctx: DetectionContext) -> ModuleResult | None:
        # 致谢
        if self.ack_pattern.match(text):
            ctx.in_references = False
            return ModuleResult(label=SectionType.ACKNOWLEDGMENT_TITLE, reason="匹配致谢模式")

        # 附录
        if self.appendix_pattern.match(text):
            return ModuleResult(label=SectionType.APPENDIX_TITLE, reason="匹配附录模式")

        return None
