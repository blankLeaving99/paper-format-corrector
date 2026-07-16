"""文档模块化检测架构。

文档被拆分为 N 类模块，每类负责自己的段落检测和上下文校验：

  title_module     → TITLE, AUTHORS, AFFILIATION
  abstract_module  → ABSTRACT_CN/EN, KEYWORDS_CN/EN
  heading_module   → CHAPTER, SECTION, SUBSECTION
  body_module      → BODY
  caption_module   → FIGURE_CAPTION, TABLE_CAPTION
  reference_module → REFERENCE_TITLE, REFERENCE_ITEM
  special_module   → CODE, FORMULA_CONTENT, FORMULA
  closing_module   → ACKNOWLEDGMENT_TITLE, APPENDIX_TITLE, TOC_TITLE

每个模块独立实现，可单独替换为神经网络版本。
"""

from .abstract_module import AbstractModule
from .base import DetectionContext, ModuleResult, SectionModule
from .body_module import BodyModule
from .caption_module import CaptionModule
from .closing_module import ClosingModule
from .heading_module import HeadingModule
from .reference_module import ReferenceModule
from .special_module import SpecialModule
from .title_module import TitleModule

__all__ = [
    "DetectionContext",
    "ModuleResult",
    "SectionModule",
    "TitleModule",
    "AbstractModule",
    "HeadingModule",
    "BodyModule",
    "CaptionModule",
    "ReferenceModule",
    "SpecialModule",
    "ClosingModule",
]
