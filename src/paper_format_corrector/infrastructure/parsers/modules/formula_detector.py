"""公式检测器 - 增强的公式段落检测。

检测特征:
  - Cambria Math / Latin Modern Math 字体
  - 居中段落 (对齐方式 = CENTER)
  - 数学符号 (∑ ∫ √ π ∂ ∞ ≤ ≥ ≠ 等 Unicode)
  - 编号模式 ((1), (1-1), Eq.(1))
  - 希腊字母 / 上下标数字
"""

from __future__ import annotations

import re

from docx.text.paragraph import Paragraph

from ..section_types import SectionType
from .base import DetectionContext, ModuleResult, SectionModule


class FormulaDetector(SectionModule):
    """增强的公式检测模块。"""

    name = "formula"

    def __init__(self, config: dict):
        detect = config.get("auto_detect", {})
        self._formula_pattern = re.compile(
            detect.get("formula_pattern", r"^\(?\d+[-\.]\d+\)?$")
        )
        self._extended_formula_pattern = re.compile(
            r"^\(?[A-Z]?\d+[-\.]\d+\)?$"       # (A1-1), (1.1)
            r"|^Eq\.?\s*\(?\d+"                 # Eq.(1), Eq. 1
            r"|^式\s*\(?\d+"                     # 式(1)
            r"|^\(\d+[a-z]?\)$"                  # (1a)
        )
        self._math_fonts: set[str] = {
            "cambria math", "latin modern math", "mt extra",
            "ms math", "math", "cambria", "symbol",
        }
        self._math_unicode = re.compile(
            r"[∀-⋿←-⇿⁰-₟Α-ω°-¹"
            r"≤≥≠∞∑∏∫√∈∉∂∇±×÷"
            r"′″‴‵‶‷≈≡∝∠⊥"
            r"⊂⊃∪∩∧∨¬⇒⇔"
            r"αβγδεζηθικλμνξπρστυφχψω"
            r"ΓΔΘΛΞΠΣΦΨΩ]"
        )
        self._greek_letters = re.compile(
            r"[αβγδεζηθικλμνξπρστυφχψω"
            r"ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΠΡΣΤΥΦΧΨΩ]"
        )
        self._sub_superscript = re.compile(r"[⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉]")

    def detect(self, para: Paragraph, text: str, ctx: DetectionContext) -> ModuleResult | None:
        if len(text) < 1:
            return None

        # 公式编号行 (高优先级)
        if self._formula_pattern.match(text) or self._extended_formula_pattern.match(text):
            return ModuleResult(
                label=SectionType.FORMULA,
                confidence=0.95,
                reason="匹配公式编号模式",
            )

        # 公式内容
        confidence, reason = self._check_formula_content(para, text)
        if confidence > 0:
            return ModuleResult(
                label=SectionType.FORMULA_CONTENT,
                confidence=confidence,
                reason=reason,
            )

        return None

    def _check_formula_content(self, para: Paragraph, text: str) -> tuple[float, str]:
        """返回 (置信度, 原因描述)"""
        # 方法1: 数学字体 (高置信度)
        font_conf = self._check_math_font(para)
        if font_conf > 0:
            return font_conf, "检测到数学字体"

        # 方法2: 数学 Unicode 字符
        if self._math_unicode.search(text):
            return 0.90, "包含数学Unicode符号"

        # 方法3: 居中 + 无中文 + 短文本 + 希腊字母/上下标
        center_conf = self._check_centered_math(para, text)
        if center_conf > 0:
            return center_conf, "居中段落含数学特征"

        # 方法4: 纯数学表达式模式 (字母+数字+运算符, 无中文)
        expr_conf = self._check_math_expression(text)
        if expr_conf > 0:
            return expr_conf, "数学表达式模式"

        return 0.0, ""

    def _check_math_font(self, para: Paragraph) -> float:
        """检查是否使用数学字体。"""
        try:
            runs = para.runs
        except AttributeError:
            return 0.0
        if not runs:
            return 0.0

        math_count = sum(
            1 for r in runs
            if (r.font.name or "").lower() in self._math_fonts
        )
        ratio = math_count / len(runs)

        if ratio >= 0.7:
            return 0.95
        if ratio >= 0.5:
            return 0.90
        if math_count > 0 and ratio >= 0.3:
            return 0.80
        return 0.0

    def _check_centered_math(self, para: Paragraph, text: str) -> float:
        """检查居中 + 无中文 + 短文本 + 数学特征。"""
        try:
            is_centered = (para.alignment == 1)  # WD_ALIGN_PARAGRAPH.CENTER
        except Exception:
            return 0.0

        if not is_centered:
            return 0.0
        if re.search(r"[一-鿿]", text):
            return 0.0
        if len(text) > 60:
            return 0.0

        # 包含希腊字母
        if self._greek_letters.search(text):
            return 0.85
        # 包含上下标
        if self._sub_superscript.search(text):
            return 0.85
        # 包含数学运算符
        math_ops = set("=+−×÷≤≥≠≈∞∑∏∫√∈∉⊂⊃∪∩∂∇±")
        if any(c in math_ops for c in text):
            return 0.80

        return 0.0

    def _check_math_expression(self, text: str) -> float:
        """检查纯数学表达式模式。"""
        if re.search(r"[一-鿿]", text):
            return 0.0
        if len(text) > 80:
            return 0.0

        math_ops = set("=+−×÷≤≥≠≈∞∑∏∫√∈∉⊂⊃∪∩∂∇±")
        op_count = sum(1 for c in text if c in math_ops)
        alpha_count = sum(1 for c in text if c.isalpha())
        digit_count = sum(1 for c in text if c.isdigit())

        # 数学表达式特征: 运算符 + (字母或数字) + 无中文标点
        if op_count >= 2 and (alpha_count + digit_count) > 0:
            total = len(text)
            op_ratio = op_count / total
            if 0.05 < op_ratio < 0.6:
                return 0.75

        return 0.0
