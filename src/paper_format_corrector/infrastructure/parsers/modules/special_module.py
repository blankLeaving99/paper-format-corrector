"""特殊内容模块：检测 CODE, FORMULA_CONTENT, FORMULA。"""

import re

from docx.text.paragraph import Paragraph

from ..section_types import SectionType
from .base import DetectionContext, ModuleResult, SectionModule


class SpecialModule(SectionModule):
    name = "special"

    def __init__(self, config: dict):
        detect = config.get("auto_detect", {})
        self.formula_pattern = re.compile(
            detect.get("formula_pattern", r"^\(?\d+[-\.]\d+\)?$")
        )
        self._mono_fonts = {
            "consolas", "courier new", "monospace", "fixedsys",
            "lucida console", "source code pro", "menlo", "monaco",
        }
        self._math_fonts = {"cambria math", "symbol", "mt extra", "math"}
        self._code_chars = set("{}();=<>[]|&!~^*/\\")
        self._math_unicode = re.compile(
            r"[∀-⋿←-⇿⁰-₟Α-ω°-¹"
            r"≤≥≠∞∑∏∫√∈∉"
            r"′″‴‵‶‷]"
        )

    def detect(self, para: Paragraph, text: str, ctx: DetectionContext) -> ModuleResult | None:
        # 代码段落（在章标题之前，避免代码中的数字被误判为标题）
        if self._is_code_paragraph(para, text):
            return ModuleResult(label=SectionType.CODE, reason="检测到等宽字体/缩进+代码字符")

        # 公式内容（非编号行的公式）
        if self._is_formula_content(para, text):
            return ModuleResult(label=SectionType.FORMULA_CONTENT, reason="检测到数学字体/Unicode数学符号")

        # 公式编号行
        if self.formula_pattern.match(text):
            return ModuleResult(label=SectionType.FORMULA, reason="匹配公式编号模式")

        return None

    def _is_code_paragraph(self, para: Paragraph, text: str) -> bool:
        if len(text) < 3:
            return False

        try:
            style_name = (para.style.name or "").lower()
            if "code" in style_name:
                return True
        except Exception:
            pass

        try:
            runs = para.runs
        except AttributeError:
            runs = []
        if runs:
            mono_count = sum(1 for r in runs if (r.font.name or "").lower() in self._mono_fonts)
            if mono_count > 0 and mono_count >= len(runs) * 0.7:
                return True

        try:
            raw_text = para.text
        except AttributeError:
            raw_text = text
        if raw_text.startswith(("    ", "\t")):
            code_chars_in_text = sum(1 for c in text if c in self._code_chars)
            if code_chars_in_text >= 2:
                return True

        return False

    def _is_formula_content(self, para: Paragraph, text: str) -> bool:
        if len(text) < 2:
            return False

        try:
            runs = para.runs
        except AttributeError:
            runs = []
        if runs:
            math_count = sum(1 for r in runs if (r.font.name or "").lower() in self._math_fonts)
            if math_count > 0 and math_count >= len(runs) * 0.5:
                return True

        if self._math_unicode.search(text):
            return True

        if not re.search(r"[一-鿿]", text):
            math_ops = set("=+−×÷≤≥≠≈∞∑∏∫√∈∉⊂⊃∪∩")
            if any(c in math_ops for c in text) and len(text) < 60:
                return True

        return False
