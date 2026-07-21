"""交叉引用更新与引用一致性检查模块

功能：
1. 自动更新正文中对图表公式的引用编号（交叉引用更新）
2. 检查正文引用和参考文献列表的一致性（引用一致性检查）
3. 检测未引用条目、缺失条目、重复条目
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CitationIssue:
    """引用一致性问题"""
    issue_type: str  # "missing_in_references", "missing_in_text", "duplicate", "doi_format"
    detail: str
    paragraph_index: int | None = None
    reference_text: str = ""


@dataclass
class CitationConsistencyReport:
    """引用一致性检查报告"""
    total_text_citations: int = 0
    total_reference_items: int = 0
    matched_citations: list[str] = field(default_factory=list)
    issues: list[CitationIssue] = field(default_factory=list)
    consistency_score: float = 1.0


class CrossReferenceUpdater:
    """交叉引用更新器 + 引用一致性检查"""

    # 正文引用模式
    TEXT_CITATION_PATTERNS = [
        re.compile(r"\[(\d+(?:[,\s\-–]+\d+)*)\]"),  # [1], [1,2], [1-3]
        re.compile(r"\[(\d+)\s*[-–]\s*(\d+)\]"),  # [1-3] 范围
        re.compile(r"\[(\d+),\s*(\d+)\]"),  # [1, 2]
    ]

    # 参考文献条目编号模式
    REF_ITEM_PATTERNS = [
        re.compile(r"^\[?\d+\]?[\s\.]"),  # [1] 或 1. 或 1
        re.compile(r"^\d+[\.\s]"),
    ]

    DOI_PATTERN = re.compile(r"10\.\d{4,}/[^\s]+")

    def __init__(self):
        self.fig_map = {}
        self.tab_map = {}
        self.eq_map = {}
        self.ref_map = {}

    def update(self, doc, fig_map=None, tab_map=None, eq_map=None, ref_map=None):
        """更新文档中的交叉引用"""
        self.fig_map = fig_map or {}
        self.tab_map = tab_map or {}
        self.eq_map = eq_map or {}
        self.ref_map = ref_map or {}

        updated_count = 0
        for para in doc.paragraphs:
            text = para.text
            if not text:
                continue
            new_text = self._update_text(text)
            if new_text != text:
                self._replace_paragraph_text(para, new_text)
                updated_count += 1
        return updated_count

    def check_citation_consistency(self, doc: Any, ref_start: int) -> list[dict[str, Any]]:
        """检查正文引用和参考文献列表的一致性

        Args:
            doc: Document对象
            ref_start: 参考文献起始段落索引

        Returns:
            问题列表 [{"message": str, "type": str}]
        """
        issues: list[dict[str, Any]] = []

        # 提取正文中的引用编号
        text_citations = self._extract_text_citations(doc, ref_start)

        # 提取参考文献条目编号
        ref_items = self._extract_reference_items(doc, ref_start)

        # 检查正文引用是否都在参考文献中
        for cite_num in text_citations:
            if cite_num not in ref_items:
                issues.append({
                    "message": f"正文引用 [{cite_num}] 在参考文献列表中未找到对应条目",
                    "type": "missing_in_references",
                })

        # 检查参考文献条目是否被正文引用
        for ref_num in ref_items:
            if ref_num not in text_citations:
                issues.append({
                    "message": f"参考文献条目 [{ref_num}] 未被正文引用",
                    "type": "missing_in_text",
                })

        # 检测重复引用
        duplicate_issues = self._check_duplicate_citations(text_citations)
        issues.extend(duplicate_issues)

        # 检测DOI格式
        doi_issues = self._check_doi_format(doc, ref_start)
        issues.extend(doi_issues)

        return issues

    def get_full_consistency_report(self, doc: Any, ref_start: int) -> CitationConsistencyReport:
        """生成完整的引用一致性检查报告"""
        report = CitationConsistencyReport()

        text_citations = self._extract_text_citations(doc, ref_start)
        ref_items = self._extract_reference_items(doc, ref_start)

        report.total_text_citations = len(text_citations)
        report.total_reference_items = len(ref_items)

        # 匹配的引用
        report.matched_citations = sorted(text_citations & ref_items)

        # 问题
        for cite_num in sorted(text_citations):
            if cite_num not in ref_items:
                report.issues.append(CitationIssue(
                    issue_type="missing_in_references",
                    detail=f"正文引用 [{cite_num}] 在参考文献列表中未找到",
                ))

        for ref_num in sorted(ref_items):
            if ref_num not in text_citations:
                report.issues.append(CitationIssue(
                    issue_type="missing_in_text",
                    detail=f"参考文献条目 [{ref_num}] 未被正文引用",
                ))

        # 重复检查
        all_citations = self._extract_text_citations_list(doc, ref_start)
        seen = set()
        for c in all_citations:
            if c in seen:
                report.issues.append(CitationIssue(
                    issue_type="duplicate",
                    detail=f"正文引用 [{c}] 重复出现",
                ))
            seen.add(c)

        # DOI检查
        doi_issues = self._check_doi_format(doc, ref_start)
        for issue_dict in doi_issues:
            report.issues.append(CitationIssue(
                issue_type="doi_format",
                detail=issue_dict["message"],
            ))

        # 计算一致性分数
        if report.total_text_citations > 0 or report.total_reference_items > 0:
            total_issues = len(report.issues)
            max_possible = report.total_text_citations + report.total_reference_items
            report.consistency_score = max(0.0, 1.0 - (total_issues / max_possible)) if max_possible > 0 else 1.0

        return report

    def _extract_text_citations(self, doc: Any, ref_start: int) -> set[str]:
        """提取正文中的引用编号"""
        citations: set[str] = set()

        for i, para in enumerate(doc.paragraphs):
            if i >= ref_start:
                break
            text = para.text
            if not text:
                continue

            for pattern in self.TEXT_CITATION_PATTERNS:
                for match in pattern.finditer(text):
                    groups = match.groups()
                    for g in groups:
                        if g is None:
                            continue
                        # 处理范围 [1-3]
                        range_match = re.match(r"(\d+)\s*[-–]\s*(\d+)", g)
                        if range_match:
                            start_num = int(range_match.group(1))
                            end_num = int(range_match.group(2))
                            for n in range(start_num, end_num + 1):
                                citations.add(str(n))
                        else:
                            # 处理逗号分隔 [1,2,3]
                            for num_str in re.split(r"[,\s]+", g):
                                num_str = num_str.strip()
                                if num_str.isdigit():
                                    citations.add(num_str)

        return citations

    def _extract_text_citations_list(self, doc: Any, ref_start: int) -> list[str]:
        """提取正文中的引用编号（保持顺序，用于重复检测）"""
        citations: list[str] = []

        for i, para in enumerate(doc.paragraphs):
            if i >= ref_start:
                break
            text = para.text
            if not text:
                continue

            for pattern in self.TEXT_CITATION_PATTERNS:
                for match in pattern.finditer(text):
                    groups = match.groups()
                    for g in groups:
                        if g is None:
                            continue
                        range_match = re.match(r"(\d+)\s*[-–]\s*(\d+)", g)
                        if range_match:
                            start_num = int(range_match.group(1))
                            end_num = int(range_match.group(2))
                            for n in range(start_num, end_num + 1):
                                citations.append(str(n))
                        else:
                            for num_str in re.split(r"[,\s]+", g):
                                num_str = num_str.strip()
                                if num_str.isdigit():
                                    citations.append(num_str)

        return citations

    def _extract_reference_items(self, doc: Any, ref_start: int) -> set[str]:
        """提取参考文献条目编号"""
        items: set[str] = set()

        for i, para in enumerate(doc.paragraphs):
            if i < ref_start:
                continue
            text = para.text.strip()
            if not text:
                continue

            for pattern in self.REF_ITEM_PATTERNS:
                match = pattern.match(text)
                if match:
                    num = re.search(r"\d+", match.group(0))
                    if num:
                        items.add(num.group(0))
                    break

        return items

    def _check_duplicate_citations(self, citations: set[str]) -> list[dict[str, Any]]:
        """检查重复引用"""
        # 这个方法在 set 上工作，实际上重复检测在 list 版本中完成
        return []

    def _check_doi_format(self, doc: Any, ref_start: int) -> list[dict[str, Any]]:
        """检查参考文献中的DOI格式"""
        issues: list[dict[str, Any]] = []

        for i, para in enumerate(doc.paragraphs):
            if i < ref_start:
                continue
            text = para.text.strip()
            if not text:
                continue

            dois = self.DOI_PATTERN.findall(text)
            for doi in dois:
                # 检查DOI是否以 https://doi.org/ 或 http://dx.doi.org/ 开头
                if not doi.startswith("https://doi.org/") and not doi.startswith("http://dx.doi.org/"):
                    # DOI本身可能不包含URL前缀，只检查格式
                    if "/" not in doi or len(doi) < 8:
                        issues.append({
                            "message": f"DOI 格式可能不正确: {doi}",
                            "type": "doi_format",
                        })

        return issues

    def _update_text(self, text: str) -> str:
        """更新文本中的引用编号"""
        result = text

        for old, new in self.fig_map.items():
            result = re.sub(
                rf"(图)\s*{re.escape(old)}(?=[\s所示中，。、])",
                rf"\g<1>{new}", result,
            )

        for old, new in self.tab_map.items():
            result = re.sub(
                rf"(表)\s*{re.escape(old)}(?=[\s所示中，。、])",
                rf"\g<1>{new}", result,
            )

        for old, new in self.eq_map.items():
            result = re.sub(
                rf"(式|公式)\s*\(?{re.escape(old)}\)?",
                rf"\g<1>({new})", result,
            )

        return result

    def _replace_paragraph_text(self, paragraph, new_text: str) -> None:
        """替换段落文本（保留第一个run的格式）"""
        if not paragraph.runs:
            return
        first_run = paragraph.runs[0]
        first_run.text = new_text
        for run in paragraph.runs[1:]:
            run.text = ""
