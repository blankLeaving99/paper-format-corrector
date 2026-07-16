"""正文模块：检测 BODY。"""

from docx.text.paragraph import Paragraph

from ..section_types import SectionType
from .base import DetectionContext, ModuleResult, SectionModule


class BodyModule(SectionModule):
    name = "body"

    def __init__(self, config: dict):
        pass  # 兜底模块，无需配置

    def detect(self, para: Paragraph, text: str, ctx: DetectionContext) -> ModuleResult | None:
        # BodyModule 是兜底模块：只要其他模块都没匹配，就标记为 BODY。
        # 由编排器在所有其他模块之后调用。
        return ModuleResult(label=SectionType.BODY, confidence=0.5, reason="默认正文")
