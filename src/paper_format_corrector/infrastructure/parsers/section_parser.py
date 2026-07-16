import re
from typing import Any

from .modules.abstract_module import AbstractModule
from .modules.base import DetectionContext, SectionModule
from .modules.body_module import BodyModule
from .modules.caption_module import CaptionModule
from .modules.closing_module import ClosingModule
from .modules.heading_module import HeadingModule
from .modules.reference_module import ReferenceModule
from .modules.special_module import SpecialModule
from .modules.title_module import TitleModule
from .section_types import (
    DetectionPipelineResult,
    LevelCorrection,
    SectionType,
)


class SectionDetector:
    """智能段落类型检测器。

    检测架构：
      文档 → [标题模块, 摘要模块, 标题层级模块, 图表模块,
              参考文献模块, 特殊内容模块, 结尾模块, 正文模块]
           → 聚合（首个匹配的模块胜出）
           → 跨模块上下文校验
           → 最终结果
    """

    def __init__(self, config):
        self.config = config

        # 初始化各检测模块（按检测优先级排列）
        self._modules: list[SectionModule] = [
            ReferenceModule(config),   # 参考文献（有状态，需在其他模块之前）
            TitleModule(config),       # 标题页
            AbstractModule(config),    # 摘要/关键词
            ClosingModule(config),     # 致谢/附录
            SpecialModule(config),     # 代码/公式（在标题之前，避免代码数字误判）
            HeadingModule(config),     # 章/节/小节标题
            CaptionModule(config),     # 图注/表注
            BodyModule(config),        # 正文（兜底，最后）
        ]

        # 保留原有接口的兼容属性（detect() 方法仍使用）
        detect = config.get("auto_detect", {})
        self.title_pattern = re.compile(detect.get("title_pattern", r"^论文题目"))
        self.chapter_pattern = re.compile(
            detect.get("chapter_pattern", r"^第[一二三四五六七八九十百零\d]+[章部分篇]")
        )
        self.section_pattern = re.compile(detect.get("section_pattern", r"^\d+\.\d+"))
        self.subsection_pattern = re.compile(
            detect.get("subsection_pattern", r"^\d+\.\d+\.\d+")
        )
        self.abstract_pattern = re.compile(
            detect.get("abstract_pattern", r"^摘\s*要$|^Abstract$|^ABSTRACT$")
        )
        self.abstract_en_pattern = re.compile(
            detect.get("abstract_en_pattern", r"^Abstract$|^ABSTRACT$")
        )
        self.keywords_pattern = re.compile(
            detect.get("keywords_pattern", r"^关键词[:：]|^Key\s*[Ww]ords[:：]?")
        )
        self.ref_keywords = detect.get("reference_keywords", ["参考文献"])
        self.ack_pattern = re.compile(
            detect.get("acknowledgment_pattern", r"^致\s*谢$")
        )
        self.appendix_pattern = re.compile(
            detect.get("appendix_pattern", r"^附\s*录[A-Z]?")
        )
        self.fig_caption_pattern = re.compile(
            detect.get("figure_caption_pattern", r"^图\s*\d")
        )
        self.tab_caption_pattern = re.compile(
            detect.get("table_caption_pattern", r"^表\s*\d")
        )
        self.formula_pattern = re.compile(
            detect.get("formula_pattern", r"^\(?\d+[-\.]\d+\)?$")
        )

        # 状态跟踪（detect() 使用）
        self._seen_title = False
        self._seen_abstract_cn = False
        self._seen_abstract_en = False
        self._in_references = False
        self._chapter_count = 0

        # 代码/公式检测配置（detect() 使用）
        self._mono_fonts = {"consolas", "courier new", "monospace", "fixedsys", "lucida console", "source code pro", "menlo", "monaco"}
        self._math_fonts = {"cambria math", "symbol", "mt extra", "math"}
        self._code_chars = set("{}();=<>[]|&!~^*/\\")
        self._math_unicode = re.compile(
            r"[∀-⋿←-⇿⁰-₟Α-ω°-¹"
            r"≤≥≠∞∑∏∫√∈∉"
            r"′″‴‵‶‷]"
        )

    def reset(self):
        self._seen_title = False
        self._seen_abstract_cn = False
        self._seen_abstract_en = False
        self._in_references = False
        self._chapter_count = 0

    # ========== 单段检测（保留原有接口，向后兼容） ==========

    def detect(self, paragraph):  # noqa: C901
        """检测段落类型，返回 (SectionType, extra_info)"""
        text = paragraph.text.strip()

        if not text:
            return SectionType.BLANK, {}

        # 参考文献条目 (在参考文献区域内)
        if self._in_references:
            if self._is_reference_item(text):
                return SectionType.REFERENCE_ITEM, {}
            else:
                # 退出参考文献区域
                self._in_references = False

        # 参考文献标题
        if text.strip() in self.ref_keywords or any(
            text.strip().startswith(kw) for kw in self.ref_keywords
        ):
            self._in_references = True
            return SectionType.REFERENCE_TITLE, {}

        # 摘要
        if self.abstract_pattern.match(text):
            if self.abstract_en_pattern.match(text):
                self._seen_abstract_en = True
                return SectionType.ABSTRACT_EN, {}
            self._seen_abstract_cn = True
            return SectionType.ABSTRACT_CN, {}

        # 关键词
        if self.keywords_pattern.match(text):
            is_en = bool(re.search(r"[Kk]ey\s*[Ww]ords", text))
            return (SectionType.KEYWORDS_EN if is_en else SectionType.KEYWORDS_CN), {}

        # 题目（仅第一段，未见过标题时）
        if not self._seen_title and self.title_pattern.match(text):
            self._seen_title = True
            return SectionType.TITLE, {}

        # 致谢
        if self.ack_pattern.match(text):
            self._in_references = False
            return SectionType.ACKNOWLEDGMENT_TITLE, {}

        # 附录
        if self.appendix_pattern.match(text):
            return SectionType.APPENDIX_TITLE, {}

        # 代码段落检测（在章标题之前，避免代码中的数字被误判为标题）
        if self._is_code_paragraph(paragraph, text):
            return SectionType.CODE, {}

        # 公式内容检测（非编号行的公式）
        if self._is_formula_content(paragraph, text):
            return SectionType.FORMULA_CONTENT, {}

        # 章标题
        if self.chapter_pattern.match(text):
            self._chapter_count += 1
            return SectionType.CHAPTER, {"chapter_num": self._chapter_count}

        # 图标题
        if self.fig_caption_pattern.match(text):
            return SectionType.FIGURE_CAPTION, self._parse_caption_num(text, "图")

        # 表标题
        if self.tab_caption_pattern.match(text):
            return SectionType.TABLE_CAPTION, self._parse_caption_num(text, "表")

        # 公式编号行（只有编号的行）
        if self.formula_pattern.match(text):
            return SectionType.FORMULA, {}

        # 小节标题 (x.x.x) 必须在节标题之前检测
        if self.subsection_pattern.match(text):
            return SectionType.SUBSECTION, {}

        # 节标题 (x.x)
        if self.section_pattern.match(text):
            return SectionType.SECTION, {}

        # 作者行检测（在标题之后，包含多个2-4字中文名用空格/逗号分隔）
        if self._is_author_line(text):
            return SectionType.AUTHORS, {}

        # 启发式标题检测（根据字体属性推断）
        heuristic = self._heuristic_heading(paragraph, text)
        if heuristic is not None:
            return heuristic

        # 正文
        return SectionType.BODY, {}

    def _is_reference_item(self, text):
        """判断是否为参考文献条目"""
        # 以 [1], [2] 等开头 (IEEE, Nature, Science style)
        if re.match(r"^\[\d+\]", text):
            return True
        # 以数字 1. 2. 开头 (numbered references)
        if re.match(r"^\d+[\.\)]\s", text):
            return True
        # APA style: starts with author name(s) and year in parentheses
        # e.g., "Smith, J. (2020). Title of the paper..."
        if re.match(r"^[A-Z][a-z]+,?\s+[A-Z]\.", text) and re.search(r"\(\d{4}\)", text):
            return True
        return False

    def _is_author_line(self, text):
        """简单判断是否为作者行"""
        if len(text) > 80:
            return False
        # 包含多个中文人名（2-4个字，用空格/逗号/、分隔）
        names = re.split(r"[,，、\s]+", text)
        if len(names) >= 2:
            cn_names = [n for n in names if re.match(r"^[一-鿿]{2,4}$", n)]
            if len(cn_names) >= 2:
                return True
        # English: "First Last, First Last, and First Last" or "F. Last, F. Last"
        if re.match(r"^[A-Z][a-z]+\.?\s+[A-Z][a-z]+", text):
            # Count author-like patterns
            en_authors = re.findall(r"[A-Z][a-z]+\.?\s+[A-Z][a-z]+", text)
            if len(en_authors) >= 2:
                return True
        return False

    def _is_code_paragraph(self, paragraph, text):  # noqa: C901
        """检测是否为代码段落"""
        # 短文本跳过（避免误判）
        if len(text) < 3:
            return False

        # 方法1：检查样式名是否包含 "Code"
        try:
            style_name = (paragraph.style.name or "").lower()
            if "code" in style_name:
                return True
        except Exception:
            pass

        # 方法2：检查 runs 的字体是否为等宽字体
        try:
            runs = paragraph.runs
        except AttributeError:
            runs = []
        if runs:
            mono_count = 0
            for run in runs:
                font_name = (run.font.name or "").lower()
                if font_name in self._mono_fonts:
                    mono_count += 1
            # 大部分 run 使用等宽字体
            if mono_count > 0 and mono_count >= len(runs) * 0.7:
                return True

        # 方法3：原始文本首行缩进 + 包含代码特征字符
        try:
            raw_text = paragraph.text  # 未 strip 的原始文本
        except AttributeError:
            raw_text = text
        if raw_text.startswith(("    ", "\t")):
            code_chars_in_text = sum(1 for c in text if c in self._code_chars)
            if code_chars_in_text >= 2:
                return True

        return False

    def _is_formula_content(self, paragraph, text):  # noqa: C901
        """检测是否为公式内容（非编号行）"""
        # 短文本跳过
        if len(text) < 2:
            return False

        # 方法1：检查字体是否为数学字体
        try:
            runs = paragraph.runs
        except AttributeError:
            runs = []
        if runs:
            math_count = 0
            for run in runs:
                font_name = (run.font.name or "").lower()
                if font_name in self._math_fonts:
                    math_count += 1
            if math_count > 0 and math_count >= len(runs) * 0.5:
                return True

        # 方法2：包含数学 Unicode 字符
        if self._math_unicode.search(text):
            return True

        # 方法3：纯数学表达式模式（字母、数字、运算符、空格组成，无中文）
        if not re.search(r"[一-鿿]", text):
            # 检查是否包含数学运算符
            math_ops = set("=+−×÷≤≥≠≈∞∑∏∫√∈∉⊂⊃∪∩")
            if any(c in math_ops for c in text):
                # 且文本较短，像公式而非句子
                if len(text) < 60:
                    return True

        return False

    def _heuristic_heading(self, paragraph, text):
        """启发式标题检测：根据字体属性推断疑似标题

        很多论文的标题不使用 Word 样式，而是手动设置加粗+大字号。
        此方法通过字体属性推断这些"硬编码"的标题。

        Returns:
            SectionType or None: 推断的标题类型，或 None 表示不是标题
        """
        # 短文本才可能是标题（< 80 字符）
        if len(text) > 80:
            return None

        try:
            runs = paragraph.runs
        except AttributeError:
            return None

        if not runs:
            return None

        # 统计第一个 run 的属性（代表段落主要格式）
        first_run = runs[0]
        try:
            is_bold = first_run.font.bold
            font_size = first_run.font.size
            font_size_pt = font_size.pt if font_size else None
        except Exception:
            return None

        if not is_bold:
            return None

        # 检查对齐方式
        try:
            alignment = paragraph.alignment
            is_centered = (alignment == 1)  # WD_ALIGN_PARAGRAPH.CENTER = 1
        except Exception:
            is_centered = False

        # 章标题启发式：加粗 + 居中 + 短文本 + 大字号 (>= 14pt)
        if is_centered and font_size_pt and font_size_pt >= 14:
            # 排除纯数字行、公式编号等
            if not re.match(r"^[\d\s\.\-\(\)]+$", text):
                self._chapter_count += 1
                return SectionType.CHAPTER, {"chapter_num": self._chapter_count}

        # 节标题启发式：加粗 + 大字号 (>= 13pt) + 短文本
        if font_size_pt and font_size_pt >= 13 and len(text) < 50:
            return SectionType.SECTION, {}

        return None

    def _parse_caption_num(self, text, prefix):
        """解析图表编号，如 '图1-2 xxx' -> {'num': '1-2'}, 'Fig. 1 xxx' -> {'num': '1'}"""
        # Handle abbreviated prefixes like "Fig.", "Fig", "TABLE"
        escaped = re.escape(prefix)
        m = re.match(rf"^{escaped}\.?\s*(\d+[\-\.]\d+|\d+)", text, re.IGNORECASE)
        if m:
            return {"num": m.group(1)}
        return {}

    # ========== 多模块检测管道 ==========

    def detect_all(self, paragraphs):
        """多模块检测管道入口。

        架构：
          文档 → 各模块独立检测 → 聚合（首个匹配胜出）→ 跨模块校验 → 最终结果

        Returns:
            DetectionPipelineResult
        """
        ctx = DetectionContext()
        n = len(paragraphs)

        # 初始化结果容器
        module_labels: dict[str, list[SectionType]] = {
            m.name: [SectionType.UNKNOWN] * n for m in self._modules
        }
        module_extras: dict[str, list[dict]] = {
            m.name: [{}] * n for m in self._modules
        }
        final_labels = [SectionType.UNKNOWN] * n
        final_extras: list[dict[str, Any]] = [{}] * n
        all_corrections: list[LevelCorrection] = []

        # 收集章节标题用于页眉页脚
        self._chapter_map: dict[int, str] = {}

        # ---- 第一轮：各模块独立检测，聚合首个匹配 ----
        for i, para in enumerate(paragraphs):
            text = para.text.strip()
            if not text:
                final_labels[i] = SectionType.BLANK
                continue

            for module in self._modules:
                result = module.detect(para, text, ctx)
                module_labels[module.name][i] = result.label if result else SectionType.UNKNOWN
                if result and result.extras:
                    module_extras[module.name][i] = result.extras

                # 首个匹配的模块胜出
                if result and final_labels[i] == SectionType.UNKNOWN:
                    final_labels[i] = result.label
                    final_extras[i] = result.extras

            # 收集章标题文本
            if final_labels[i] == SectionType.CHAPTER:
                self._chapter_map[i] = text

        # ---- 第二轮：各模块跨段落校验 ----
        for module in self._modules:
            corrections = module.validate(paragraphs, final_labels, ctx)
            for corr in corrections:
                idx = corr["index"]
                old_label = final_labels[idx]
                new_label = corr["to"]
                if old_label != new_label:
                    final_labels[idx] = new_label
                    all_corrections.append(LevelCorrection(
                        index=idx,
                        from_label=old_label,
                        to_label=new_label,
                        reason=corr["reason"],
                        module=module.name,
                    ))

        return DetectionPipelineResult(
            final_labels=final_labels,
            final_extras=final_extras,
            module_results=module_labels,
            all_corrections=all_corrections,
        )

    def get_chapter_map(self):
        """返回 {paragraph_index: chapter_name} 映射，用于页眉页脚。

        在 detect_all() 调用后才有效。
        """
        return getattr(self, "_chapter_map", {})


def detect_language(text):
    """检测文本主要语言

    Returns: "chinese" | "english" | "japanese" | "korean" | "mixed"
    """
    if not text:
        return "unknown"

    cn_count = len(re.findall(r"[一-鿿]", text))
    jp_count = len(re.findall(r"[぀-ゟ゠-ヿ]", text))
    kr_count = len(re.findall(r"[가-힯ᄀ-ᇿ]", text))
    en_count = len(re.findall(r"[a-zA-Z]", text))
    total = cn_count + jp_count + kr_count + en_count

    if total == 0:
        return "unknown"

    # 日文假名优先检测
    if jp_count > total * 0.1:
        return "japanese"
    # 韩文
    if kr_count > total * 0.1:
        return "korean"
    # 中文
    if cn_count > en_count:
        return "chinese"
    # 英文
    if en_count > cn_count:
        return "english"

    return "mixed"


def detect_document_language(doc):
    """检测整个文档的主要语言"""
    from collections import Counter
    lang_counter = Counter()
    sample_count = 0

    for para in doc.paragraphs:
        text = para.text.strip()
        if len(text) < 5:
            continue
        lang = detect_language(text)
        if lang != "unknown":
            lang_counter[lang] += 1
            sample_count += 1
        if sample_count >= 50:  # 采样前50段即可
            break

    if not lang_counter:
        return "chinese"  # 默认中文

    return lang_counter.most_common(1)[0][0]
