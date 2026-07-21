"""模块基类和共享数据结构。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from docx.text.paragraph import Paragraph

from ..section_types import SectionType


@dataclass
class DetectionContext:
    """跨模块共享的检测上下文。

    各模块在检测过程中读写此上下文，实现有状态的检测
    （如"标题只出现一次"、"进入参考文献区域"等）。
    """

    seen_title: bool = False
    seen_abstract_cn: bool = False
    seen_abstract_en: bool = False
    in_references: bool = False
    chapter_count: int = 0


@dataclass
class ModuleResult:
    """单个模块对单个段落的检测结果。"""

    label: SectionType
    extras: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    reason: str = ""


class SectionModule:
    """文档模块基类。

    每个子类负责一类段落的检测。子类必须实现 detect() 方法，
    可选实现 validate() 方法进行跨段落校验。
    """

    name: str = "base"

    def __init__(self, config: dict):
        pass

    def detect(self, para: Paragraph, text: str, ctx: DetectionContext) -> ModuleResult | None:
        """检测单个段落。

        Args:
            para: Paragraph 对象
            text: strip 后的文本
            ctx: 共享上下文

        Returns:
            ModuleResult 如果匹配本模块负责的类型，否则 None
        """
        return None

    def validate(
        self,
        paragraphs: list[Paragraph],
        labels: list[SectionType],
        ctx: DetectionContext,
    ) -> list[dict]:
        """跨段落上下文校验（可选）。

        Args:
            paragraphs: 所有段落
            labels: 当前所有段落的标签（可原地修改）
            ctx: 共享上下文

        Returns:
            修正记录列表 [{"index": int, "from": SectionType, "to": SectionType, "reason": str}]
        """
        return []
