"""段落类型定义和检测结果数据结构。

独立成文件，避免 section_detector ↔ modules 循环导入。
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class SectionType(Enum):
    UNKNOWN = auto()
    TITLE = auto()
    AUTHORS = auto()
    AFFILIATION = auto()
    ABSTRACT_CN = auto()
    ABSTRACT_EN = auto()
    KEYWORDS_CN = auto()
    KEYWORDS_EN = auto()
    CHAPTER = auto()
    SECTION = auto()
    SUBSECTION = auto()
    BODY = auto()
    FIGURE_CAPTION = auto()
    TABLE_CAPTION = auto()
    FORMULA = auto()
    FORMULA_CONTENT = auto()
    CODE = auto()
    REFERENCE_TITLE = auto()
    REFERENCE_ITEM = auto()
    ACKNOWLEDGMENT = auto()
    ACKNOWLEDGMENT_TITLE = auto()
    APPENDIX_TITLE = auto()
    TOC_TITLE = auto()
    BLANK = auto()


@dataclass
class LevelCorrection:
    """单条修正记录。"""
    index: int
    from_label: SectionType
    to_label: SectionType
    reason: str
    module: str  # 产生修正的模块名


@dataclass
class DetectionPipelineResult:
    """多模块检测管道的最终输出。"""
    final_labels: list[SectionType]
    final_extras: list[dict[str, Any]]
    module_results: dict[str, list[SectionType]]  # 每个模块的检测结果
    all_corrections: list[LevelCorrection]
