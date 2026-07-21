"""PDF style extractor - reverse learning styles from PDF documents.

This module extracts formatting information from PDF files using pdfplumber
to help learn and replicate document styles.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PDFTextBlock:
    """A block of text extracted from a PDF page."""

    text: str
    font_name: str = ""
    font_size: float = 12.0
    is_bold: bool = False
    is_italic: bool = False
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 14.0
    page_width: float = 595.0
    page_height: float = 842.0
    page_num: int = 0


@dataclass
class PDFPageInfo:
    """Information about a single PDF page."""

    page_num: int
    width: float = 595.0
    height: float = 842.0
    text_blocks: list[PDFTextBlock] = field(default_factory=list)


# ── Chinese heading patterns ──────────────────────────────────────
_CHAPTER_PATTERNS = [
    re.compile(r"^[第第]?[一二三四五六七八九十百]+[章节篇]"),
    re.compile(r"^Chapter\s+\d+", re.IGNORECASE),
    re.compile(r"^\d+\s+[\u4e00-\u9fff]"),  # "1 引言"
]
_HEADING2_PATTERNS = [
    re.compile(r"^\d+\.\d+\s+[\u4e00-\u9fff]"),  # "1.1 研究背景"
    re.compile(r"^\d+\.\d+\s+[A-Z]"),
]
_HEADING3_PATTERNS = [
    re.compile(r"^\d+\.\d+\.\d+\s+"),  # "1.1.1 ..."
]

# ── Special section patterns ──────────────────────────────────────
_ABSTRACT_PATTERNS = [
    re.compile(r"^摘\s*要\s*$"),
    re.compile(r"^Abstract\s*$", re.IGNORECASE),
    re.compile(r"^ABSTRACT\s*$"),
]
_KEYWORDS_PATTERNS = [
    re.compile(r"^(?:关\s*键\s*词|关键字)\s*[：:]", re.IGNORECASE),
    re.compile(r"^Keywords?\s*:", re.IGNORECASE),
    re.compile(r"^KEY\s*WORDS?\s*:", re.IGNORECASE),
]
_REFERENCE_TITLE_PATTERNS = [
    re.compile(r"^参\s*考\s*文\s*献\s*$"),
    re.compile(r"^References\s*$", re.IGNORECASE),
    re.compile(r"^BIBLIOGRAPHY\s*$", re.IGNORECASE),
]
_REFERENCE_ENTRY_PATTERN = re.compile(r"^\[\d+\]")
_FIGURE_CAPTION_PATTERN = re.compile(
    r"^(?:图\s*\d|Figure\s+\d+|Fig\.\s*\d+)", re.IGNORECASE
)
_TABLE_CAPTION_PATTERN = re.compile(
    r"^(?:表\s*\d|Table\s+\d+)", re.IGNORECASE
)


def _classify_block(block: PDFTextBlock) -> str:
    """Classify a text block into a paragraph type.

    Returns one of: heading1, heading2, heading3, abstract_title, keywords,
    reference, figure_caption, table_caption, body
    """
    text = block.text.strip()
    if not text:
        return "body"

    # Abstract title check (before heading check since abstract titles are bold+large)
    for pat in _ABSTRACT_PATTERNS:
        if pat.match(text):
            return "abstract_title"

    # Keywords
    for pat in _KEYWORDS_PATTERNS:
        if pat.match(text):
            return "keywords"

    # Reference title
    for pat in _REFERENCE_TITLE_PATTERNS:
        if pat.match(text):
            return "reference"

    # Reference entry (starts with [1], [2], etc.)
    if _REFERENCE_ENTRY_PATTERN.match(text):
        return "reference"

    # Figure caption
    if _FIGURE_CAPTION_PATTERN.match(text):
        return "figure_caption"

    # Table caption
    if _TABLE_CAPTION_PATTERN.match(text):
        return "table_caption"

    # Chapter / heading1 (large + bold, or matches chapter pattern)
    is_chapter = any(pat.match(text) for pat in _CHAPTER_PATTERNS)
    if is_chapter or (block.font_size >= 15 and block.is_bold):
        return "heading1"

    # heading3 (matches 1.1.1 pattern)
    if any(pat.match(text) for pat in _HEADING3_PATTERNS):
        return "heading3"

    # heading2 (matches 1.1 pattern, or bold + moderate size)
    is_h2 = any(pat.match(text) for pat in _HEADING2_PATTERNS)
    if is_h2:
        return "heading2"
    if block.is_bold and block.font_size >= 12:
        # Bold text with moderate size → heading2
        if len(text) <= 30:  # Short bold text is likely a heading
            return "heading2"
        if block.font_size >= 13:
            return "heading2"

    # Default: body text
    return "body"


def _dominant_body_rule(blocks: list[PDFTextBlock]) -> dict[str, Any] | None:
    """Determine the dominant body text formatting rule.

    Returns None if no body blocks found, otherwise returns a dict with
    font_size, bold, font_name, etc.
    """
    if not blocks:
        return None

    body_blocks = [b for b in blocks if _classify_block(b) == "body"]
    if not body_blocks:
        return None

    sizes = [b.font_size for b in body_blocks]
    size_counter = Counter(sizes)
    dominant_size = size_counter.most_common(1)[0][0]

    bolds = [b.is_bold for b in body_blocks]
    dominant_bold = Counter(bolds).most_common(1)[0][0]

    fonts = [b.font_name for b in body_blocks if b.font_name]
    dominant_font = Counter(fonts).most_common(1)[0][0] if fonts else ""

    return {
        "font_size": dominant_size,
        "bold": dominant_bold,
        "font_name": dominant_font,
    }


def _dominant_heading_rule(blocks: list[PDFTextBlock]) -> dict[str, Any] | None:
    """Determine the dominant heading formatting rule.

    Returns None if no heading blocks found, otherwise returns a dict with
    font_size, bold, font_name, etc.
    """
    if not blocks:
        return None

    heading_types = {"heading1", "heading2", "heading3", "abstract_title"}
    heading_blocks = [b for b in blocks if _classify_block(b) in heading_types]
    if not heading_blocks:
        return None

    sizes = [b.font_size for b in heading_blocks]
    dominant_size = Counter(sizes).most_common(1)[0][0]

    bolds = [b.is_bold for b in heading_blocks]
    dominant_bold = Counter(bolds).most_common(1)[0][0]

    fonts = [b.font_name for b in heading_blocks if b.font_name]
    dominant_font = Counter(fonts).most_common(1)[0][0] if fonts else ""

    return {
        "font_size": dominant_size,
        "bold": dominant_bold,
        "font_name": dominant_font,
    }


# ── Font name mapping ──────────────────────────────────────────────
_CN_FONT_MAP = {
    "simsun": "SimSun",
    "songti": "SimSun",
    "song": "SimSun",
    "simhei": "SimHei",
    "heiti": "SimHei",
    "kaiti": "KaiTi",
    "simkai": "KaiTi",
    "fangsong": "FangSong",
    "simfang": "FangSong",
    "microsoftyahei": "Microsoft YaHei",
    "yahei": "Microsoft YaHei",
}
_EN_FONT_MAP = {
    "timesnewroman": "TimesNewRoman",
    "times new roman": "TimesNewRoman",
    "times": "TimesNewRoman",
    "arial": "Arial",
    "calibri": "Calibri",
    "cambria": "Cambria",
    "georgia": "Georgia",
    "palatino": "Palatino",
    "garamond": "Garamond",
    "bookman": "Bookman",
}


def _infer_font_names(blocks: list[PDFTextBlock]) -> dict[str, str]:
    """Infer Chinese and English font names from PDF text blocks.

    Returns dict with 'chinese' and 'english' keys.
    """
    cn_fonts: list[str] = []
    en_fonts: list[str] = []

    for block in blocks:
        fn_lower = block.font_name.lower().strip()
        if not fn_lower or fn_lower == "unknown":
            continue

        # Check Chinese font
        for key, canonical in _CN_FONT_MAP.items():
            if key in fn_lower:
                cn_fonts.append(canonical)
                break

        # Check English font
        for key, canonical in _EN_FONT_MAP.items():
            if key in fn_lower:
                en_fonts.append(canonical)
                break

    result = {
        "chinese": Counter(cn_fonts).most_common(1)[0][0] if cn_fonts else "宋体",
        "english": Counter(en_fonts).most_common(1)[0][0] if en_fonts else "Times New Roman",
    }
    return result


def _group_chars_into_blocks(
    chars: list[dict],
    page_width: float = 595.0,
    page_height: float = 842.0,
    page_num: int = 0,
) -> list[PDFTextBlock]:
    """Group individual character info from pdfplumber into text blocks.

    Each char dict has keys: text, fontname, size, x0, x1, top, bottom.
    Characters on the same line (similar 'top') are grouped into one block.
    """
    if not chars:
        return []

    blocks: list[PDFTextBlock] = []
    current_chars: list[str] = []
    current_top: float = chars[0].get("top", 0)
    current_size: float = chars[0].get("size", 12.0)
    current_font: str = chars[0].get("fontname", "")
    current_x0: float = chars[0].get("x0", 0)

    for char_info in chars:
        top = char_info.get("top", 0)
        # New line if top differs by more than half the font size
        if abs(top - current_top) > current_size * 0.5:
            # Flush current block
            if current_chars:
                blocks.append(PDFTextBlock(
                    text="".join(current_chars),
                    font_name=current_font,
                    font_size=current_size,
                    is_bold=_is_bold_font(current_font),
                    x=current_x0,
                    y=current_top,
                    width=400,
                    height=current_size * 1.2,
                    page_width=page_width,
                    page_height=page_height,
                    page_num=page_num,
                ))
            current_chars = [char_info.get("text", "")]
            current_top = top
            current_size = char_info.get("size", current_size)
            current_font = char_info.get("fontname", current_font)
            current_x0 = char_info.get("x0", 0)
        else:
            current_chars.append(char_info.get("text", ""))

    # Flush last block
    if current_chars:
        blocks.append(PDFTextBlock(
            text="".join(current_chars),
            font_name=current_font,
            font_size=current_size,
            is_bold=_is_bold_font(current_font),
            x=current_x0,
            y=current_top,
            width=400,
            height=current_size * 1.2,
            page_width=page_width,
            page_height=page_height,
            page_num=page_num,
        ))

    return blocks


def _is_bold_font(font_name: str) -> bool:
    """Check if a font name suggests bold weight."""
    if not font_name:
        return False
    lower = font_name.lower()
    return "bold" in lower or "black" in lower or "heavy" in lower


def _extract_with_pdfplumber(pdf_path: str) -> list[PDFPageInfo]:
    """Extract page info from a PDF using pdfplumber."""
    import pdfplumber

    pages: list[PDFPageInfo] = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_info = PDFPageInfo(
                page_num=i,
                width=float(page.width),
                height=float(page.height),
            )
            chars = page.chars
            if chars:
                page_info.text_blocks = _group_chars_into_blocks(
                    chars, page.width, page.height, i
                )
            pages.append(page_info)
    return pages


def extract_pdf_style(pdf_path: str | Path) -> dict[str, Any]:
    """Extract style information from a PDF file.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Dictionary containing extracted style information as format_rules.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not a PDF.
        RuntimeError: If no text could be extracted.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"不是 PDF 文件: {pdf_path}")

    pages = _extract_with_pdfplumber(str(path))

    all_blocks: list[PDFTextBlock] = []
    for page in pages:
        all_blocks.extend(page.text_blocks)

    if not all_blocks:
        raise RuntimeError("未提取到文本块，无法分析样式")

    body_rule = _dominant_body_rule(all_blocks)
    heading_rule = _dominant_heading_rule(all_blocks)
    font_names = _infer_font_names(all_blocks)

    config: dict[str, Any] = {
        "format_rules": {
            "body_text": {
                "font_size": body_rule["font_size"] if body_rule else 12,
                "bold": body_rule["bold"] if body_rule else False,
                "font_name_cn": font_names["chinese"],
                "font_name_en": font_names["english"],
            },
            "headings": {
                "font_size": heading_rule["font_size"] if heading_rule else 16,
                "bold": heading_rule["bold"] if heading_rule else True,
                "font_name_cn": font_names["chinese"],
                "font_name_en": font_names["english"],
            },
            "_extraction": {
                "source": "pdf",
                "pages_analyzed": len(pages),
                "blocks_extracted": len(all_blocks),
                "page_width": pages[0].width if pages else 595,
                "page_height": pages[0].height if pages else 842,
            },
        },
    }
    return config
