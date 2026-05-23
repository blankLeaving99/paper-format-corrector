import re
from enum import Enum, auto


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
    REFERENCE_TITLE = auto()
    REFERENCE_ITEM = auto()
    ACKNOWLEDGMENT = auto()
    ACKNOWLEDGMENT_TITLE = auto()
    APPENDIX_TITLE = auto()
    TOC_TITLE = auto()
    BLANK = auto()


class SectionDetector:
    """智能段落类型检测器"""

    def __init__(self, config):
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

        # 状态跟踪
        self._seen_title = False
        self._seen_abstract_cn = False
        self._seen_abstract_en = False
        self._in_references = False
        self._chapter_count = 0

    def reset(self):
        self._seen_title = False
        self._seen_abstract_cn = False
        self._seen_abstract_en = False
        self._in_references = False
        self._chapter_count = 0

    def detect(self, paragraph):
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

    def _parse_caption_num(self, text, prefix):
        """解析图表编号，如 '图1-2 xxx' -> {'num': '1-2'}, 'Fig. 1 xxx' -> {'num': '1'}"""
        # Handle abbreviated prefixes like "Fig.", "Fig", "TABLE"
        escaped = re.escape(prefix)
        m = re.match(rf"^{escaped}\.?\s*(\d+[\-\.]\d+|\d+)", text, re.IGNORECASE)
        if m:
            return {"num": m.group(1)}
        return {}


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
