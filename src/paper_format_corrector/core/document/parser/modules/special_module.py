"""特殊内容模块：检测 CODE, FORMULA_CONTENT, FORMULA。

增强功能：
- 代码块检测：支持更多等宽字体、缩进+代码字符、多行代码块上下文
- 公式检测：支持更多数学Unicode字符、数学运算符、居中+无中文特征
- 公式编号行：支持多种编号格式
"""

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
            "courier", "dejavu sans mono", "liberation mono",
            "noto sans mono", "fira code", "jetbrains mono",
        }
        self._math_fonts = {
            "cambria math", "symbol", "mt extra", "math",
            "cambria", "ms math", "latin modern math",
        }
        self._code_chars = set("{}();=<>[]|&!~^*/\\#@$")
        self._math_unicode = re.compile(
            r"[∀-⋿←-⇿⁰-₟Α-ω°-¹"
            r"≤≥≠∞∑∏∫√∈∉∂∇±×÷"
            r"′″‴‵‶‷≈≡∝∠⊥"
            r"⊂⊃∪∩∧∨¬⇒⇔"
            r"αβγδεζηθικλμνξπρστυφχψω"
            r"ΓΔΘΛΞΠΣΦΨΩ]"
        )
        # 代码关键词（Python/Java/C++等常见关键字）
        self._code_keywords = {
            "def", "class", "import", "from", "return", "if", "else", "elif",
            "for", "while", "try", "except", "finally", "with", "as", "in",
            "not", "and", "or", "True", "False", "None", "self",
            "public", "private", "protected", "static", "void", "int",
            "string", "float", "double", "char", "bool", "boolean",
            "function", "var", "let", "const", "new", "this",
            "include", "define", "struct", "enum", "typedef",
        }

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

        # 方法1：检查样式名是否包含 "Code" 或 "Listing"
        try:
            style_name = (para.style.name or "").lower()
            if "code" in style_name or "listing" in style_name or "verbatim" in style_name:
                return True
        except Exception:
            pass

        # 方法2：检查 runs 的字体是否为等宽字体
        try:
            runs = para.runs
        except AttributeError:
            runs = []
        if runs:
            mono_count = sum(1 for r in runs if (r.font.name or "").lower() in self._mono_fonts)
            if mono_count > 0 and mono_count >= len(runs) * 0.7:
                return True

        # 方法3：原始文本首行缩进 + 包含代码特征字符
        try:
            raw_text = para.text
        except AttributeError:
            raw_text = text
        if raw_text.startswith(("    ", "\t")):
            code_chars_in_text = sum(1 for c in text if c in self._code_chars)
            if code_chars_in_text >= 2:
                return True

        # 方法4：检测代码关键词密度（无中文、含多个编程关键词）
        if not re.search(r"[一-鿿]", text) and len(text) < 200:
            words = set(re.findall(r"\b[a-zA-Z_]\w*\b", text))
            keyword_hits = words & self._code_keywords
            if len(keyword_hits) >= 2:
                # 还需要包含代码特征字符（括号、分号、等号等）
                code_chars_in_text = sum(1 for c in text if c in self._code_chars)
                if code_chars_in_text >= 1:
                    return True

        return False

    def _is_formula_content(self, para: Paragraph, text: str) -> bool:
        if len(text) < 2:
            return False

        # 方法1：检查字体是否为数学字体
        try:
            runs = para.runs
        except AttributeError:
            runs = []
        if runs:
            math_count = sum(1 for r in runs if (r.font.name or "").lower() in self._math_fonts)
            if math_count > 0 and math_count >= len(runs) * 0.5:
                return True

        # 方法2：包含数学 Unicode 字符
        if self._math_unicode.search(text):
            return True

        # 方法3：纯数学表达式模式（字母、数字、运算符、空格组成，无中文）
        if not re.search(r"[一-鿿]", text):
            math_ops = set("=+−×÷≤≥≠≈∞∑∏∫√∈∉⊂⊃∪∩∂∇±")
            if any(c in math_ops for c in text) and len(text) < 60:
                return True

        # 方法4：居中对齐 + 无中文 + 短文本 + 包含希腊字母或上下标
        try:
            is_centered = (para.alignment == 1)
        except Exception:
            is_centered = False
        if is_centered and not re.search(r"[一-鿿]", text) and len(text) < 40:
            # 包含希腊字母
            if re.search(r"[αβγδεζηθικλμνξπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΠΡΣΤΥΦΧΨΩ]", text):
                return True
            # 包含上下标数字
            if re.search(r"[⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉]", text):
                return True

        return False
