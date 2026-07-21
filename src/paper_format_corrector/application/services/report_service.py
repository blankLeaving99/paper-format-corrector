"""Report generation service.

Generates comprehensive modification reports in HTML, Markdown, and JSON
formats as specified in zhinan.md section 3.8.
Also supports saving report history to the database.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ReportData:
    """Structured report data"""
    input_file: str = ""
    output_file: str = ""
    template_used: str = ""
    processing_time: float = 0.0
    quality_score: float = 0.0
    applied: dict[str, int] = field(default_factory=dict)
    skipped: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    risk_items: list[dict[str, Any]] = field(default_factory=list)
    rule_sources: dict[str, str] = field(default_factory=dict)
    total_elements: int = 0
    modified_elements: int = 0
    batch_summary: dict[str, Any] | None = None
    citation_issues: list[dict[str, Any]] | None = None


class ReportService:
    """Generate correction reports in multiple formats."""

    def save_history(self, data: ReportData, database_path: str | Path | None = None) -> int:
        """Save report to processing history database. Returns record ID."""
        from ...infra.template_repository import TemplateRepository
        repo = TemplateRepository(database_path)
        return repo.save_processing_history(
            input_file=data.input_file,
            output_file=data.output_file,
            template_used=data.template_used,
            quality_score=data.quality_score,
            total_elements=data.total_elements,
            modified_elements=data.modified_elements,
            processing_time=data.processing_time,
            report={
                "applied": data.applied,
                "skipped": data.skipped,
                "warnings": data.warnings,
                "risk_items": data.risk_items,
                "rule_sources": data.rule_sources,
                "citation_issues": data.citation_issues,
            },
        )

    def generate_html(self, data: ReportData) -> str:
        """Generate a comprehensive HTML report."""
        coverage = (data.modified_elements / data.total_elements * 100) if data.total_elements > 0 else 0

        applied_rows = ""
        for key, count in data.applied.items():
            labels = {
                "paragraphs": "段落", "headings": "标题",
                "body": "正文", "tables": "表格", "images": "图片",
            }
            label = labels.get(key, key)
            applied_rows += f"<tr><td>{label}</td><td>{count}</td></tr>\n"

        skipped_rows = ""
        for item in data.skipped:
            skipped_rows += f"<tr><td>{item.get('element', '')}</td><td>{item.get('count', '')}</td><td>{item.get('reason', '')}</td></tr>\n"

        warnings_html = ""
        for w in data.warnings:
            warnings_html += f"<li class='warning'>{w}</li>\n"

        risks_html = ""
        for r in data.risk_items:
            risks_html += f"<li class='risk'><strong>{r.get('type', '')}</strong>: {r.get('detail', '')}</li>\n"

        sources_html = ""
        for key, source in data.rule_sources.items():
            sources_html += f"<tr><td>{key}</td><td>{source}</td></tr>\n"

        citation_html = ""
        if data.citation_issues:
            for issue in data.citation_issues:
                issue_type_map = {
                    "missing_in_references": "正文引用未找到对应条目",
                    "missing_in_text": "参考文献条目未被正文引用",
                    "duplicate": "重复引用",
                    "doi_format": "DOI格式问题",
                }
                type_label = issue_type_map.get(issue.get("type", ""), issue.get("type", ""))
                citation_html += f"<tr><td>{type_label}</td><td>{issue.get('message', '')}</td></tr>\n"

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>论文格式矫正报告</title>
<style>
@page {{
    size: A4;
    margin: 2cm;
    @top-center {{ content: "论文格式矫正报告"; font-size: 9pt; color: #888; }}
    @bottom-center {{ content: "第 " counter(page) " 页 / 共 " counter(pages) " 页"; font-size: 9pt; color: #888; }}
}}
@media print {{
    body {{ margin: 0; }}
    .no-print {{ display: none; }}
}}
body {{ font-family: "SimSun", "宋体", "Noto Serif CJK SC", "Source Han Serif SC", "Times New Roman", serif; margin: 20px; color: #333; line-height: 1.6; }}
.header {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #3498db; }}
.header h1 {{ margin: 0 0 10px 0; color: #2c3e50; font-family: "SimHei", "黑体", "Noto Sans CJK SC", "Source Han Sans SC", sans-serif; }}
.header p {{ margin: 4px 0; font-size: 14px; color: #555; }}
.summary {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 15px 0; }}
.stat {{ background: white; padding: 15px 20px; border-radius: 6px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1); min-width: 120px; flex: 1; }}
.stat-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
.stat-label {{ font-size: 12px; color: #666; margin-top: 5px; }}
.section {{ margin: 20px 0; page-break-inside: avoid; }}
.section h2 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px; font-family: "SimHei", "黑体", "Noto Sans CJK SC", sans-serif; }}
table {{ width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 13px; }}
th, td {{ padding: 8px 12px; border: 1px solid #ddd; text-align: left; }}
th {{ background: #f8f9fa; font-weight: 600; }}
.warning {{ color: #e67e22; }}
.risk {{ color: #e74c3c; }}
.coverage {{ background: #27ae60; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold; }}
code {{ font-family: "Consolas", "Courier New", monospace; background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-size: 13px; }}
pre {{ background: #f8f8f8; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 13px; }}
</style>
</head>
<body>
<div class="header">
<h1>论文格式矫正报告</h1>
<p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<p>输入文件: {data.input_file}</p>
<p>输出文件: {data.output_file}</p>
<p>使用模板: {data.template_used or '默认配置'}</p>
</div>

<div class="summary">
<div class="stat"><div class="stat-value">{data.total_elements}</div><div class="stat-label">总元素数</div></div>
<div class="stat"><div class="stat-value">{data.modified_elements}</div><div class="stat-label">已修改</div></div>
<div class="stat"><div class="stat-value"><span class="coverage">{coverage:.1f}%</span></div><div class="stat-label">覆盖率</div></div>
<div class="stat"><div class="stat-value">{data.quality_score:.0f}</div><div class="stat-label">质量评分</div></div>
<div class="stat"><div class="stat-value">{data.processing_time:.1f}s</div><div class="stat-label">处理耗时</div></div>
</div>

<div class="section">
<h2>已修改内容</h2>
<table>
<tr><th>类型</th><th>数量</th></tr>
{applied_rows}
</table>
</div>

{f'''<div class="section">
<h2>未修改内容</h2>
<table>
<tr><th>类型</th><th>数量</th><th>原因</th></tr>
{skipped_rows}
</table>
</div>''' if skipped_rows else ''}

{f'''<div class="section">
<h2>风险提示</h2>
<ul>{risks_html}</ul>
</div>''' if risks_html else ''}

{f'''<div class="section">
<h2>警告信息</h2>
<ul>{warnings_html}</ul>
</div>''' if warnings_html else ''}

{f'''<div class="section">
<h2>规则来源</h2>
<table>
<tr><th>规则</th><th>来源</th></tr>
{sources_html}
</table>
</div>''' if sources_html else ''}

{f'''<div class="section">
<h2>引用一致性检查</h2>
<table>
<tr><th>问题类型</th><th>详情</th></tr>
{citation_html}
</table>
</div>''' if citation_html else ''}
</body>
</html>"""

    def generate_markdown(self, data: ReportData) -> str:
        """Generate a Markdown report."""
        coverage = (data.modified_elements / data.total_elements * 100) if data.total_elements > 0 else 0

        lines = [
            "# 论文格式矫正报告",
            "",
            f"- **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **输入文件**: {data.input_file}",
            f"- **输出文件**: {data.output_file}",
            f"- **使用模板**: {data.template_used or '默认配置'}",
            "",
            "## 处理概览",
            "",
            "| 指标 | 值 |",
            "|------|-----|",
            f"| 总元素数 | {data.total_elements} |",
            f"| 已修改 | {data.modified_elements} |",
            f"| 覆盖率 | {coverage:.1f}% |",
            f"| 质量评分 | {data.quality_score:.0f}/100 |",
            f"| 处理耗时 | {data.processing_time:.1f}s |",
            "",
        ]

        if data.applied:
            lines.extend(["## 已修改内容", "", "| 类型 | 数量 |", "|------|------|"])
            labels = {"paragraphs": "段落", "headings": "标题", "body": "正文", "tables": "表格", "images": "图片"}
            for key, count in data.applied.items():
                lines.append(f"| {labels.get(key, key)} | {count} |")
            lines.append("")

        if data.skipped:
            lines.extend(["## 未修改内容", "", "| 类型 | 数量 | 原因 |", "|------|------|------|"])
            for item in data.skipped:
                lines.append(f"| {item.get('element', '')} | {item.get('count', '')} | {item.get('reason', '')} |")
            lines.append("")

        if data.risk_items:
            lines.extend(["## 风险提示", ""])
            for r in data.risk_items:
                lines.append(f"- **{r.get('type', '')}**: {r.get('detail', '')}")
            lines.append("")

        if data.warnings:
            lines.extend(["## 警告信息", ""])
            for w in data.warnings:
                lines.append(f"- {w}")
            lines.append("")

        if data.rule_sources:
            lines.extend(["## 规则来源", "", "| 规则 | 来源 |", "|------|------|"])
            for key, source in data.rule_sources.items():
                lines.append(f"| {key} | {source} |")
            lines.append("")

        if data.citation_issues:
            lines.extend(["## 引用一致性检查", "", "| 问题类型 | 详情 |", "|----------|------|"])
            issue_type_map = {
                "missing_in_references": "正文引用未找到对应条目",
                "missing_in_text": "参考文献条目未被正文引用",
                "duplicate": "重复引用",
                "doi_format": "DOI格式问题",
            }
            for issue in data.citation_issues:
                type_label = issue_type_map.get(issue.get("type", ""), issue.get("type", ""))
                lines.append(f"| {type_label} | {issue.get('message', '')} |")
            lines.append("")

        return "\n".join(lines)

    def generate_json(self, data: ReportData) -> str:
        """Generate a JSON report."""
        report = {
            "meta": {
                "generated_at": datetime.now().isoformat(),
                "input_file": data.input_file,
                "output_file": data.output_file,
                "template_used": data.template_used,
                "processing_time": round(data.processing_time, 2),
            },
            "summary": {
                "total_elements": data.total_elements,
                "modified_elements": data.modified_elements,
                "coverage_rate": round((data.modified_elements / data.total_elements * 100) if data.total_elements > 0 else 0, 1),
                "quality_score": data.quality_score,
            },
            "applied": data.applied,
            "skipped": data.skipped,
            "warnings": data.warnings,
            "risk_items": data.risk_items,
            "rule_sources": data.rule_sources,
        }
        if data.citation_issues:
            report["citation_issues"] = data.citation_issues
        if data.batch_summary:
            report["batch_summary"] = data.batch_summary
        return json.dumps(report, ensure_ascii=False, indent=2)

    def save_report(
        self,
        data: ReportData,
        output_path: str | Path,
        fmt: str = "html",
    ) -> dict[str, Any]:
        """Save report to file.

        Supported formats: html, md/markdown, json, pdf

        PDF generation uses a fallback chain:
          1. weasyprint (best Chinese support)
          2. pdfkit (requires wkhtmltopdf)
          3. xhtml2pdf (pure Python)
          4. HTML fallback (always succeeds)

        Returns:
            dict with keys: success, path, actual_fmt, engine, message
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if fmt == "html":
            content = self.generate_html(data)
            path.write_text(content, encoding="utf-8")
            return {"success": True, "path": str(path), "actual_fmt": "html", "engine": "native", "message": ""}

        if fmt in ("md", "markdown"):
            content = self.generate_markdown(data)
            path.write_text(content, encoding="utf-8")
            return {"success": True, "path": str(path), "actual_fmt": "markdown", "engine": "native", "message": ""}

        if fmt == "json":
            content = self.generate_json(data)
            path.write_text(content, encoding="utf-8")
            return {"success": True, "path": str(path), "actual_fmt": "json", "engine": "native", "message": ""}

        if fmt == "pdf":
            return self._save_pdf_with_fallback(data, path)

        raise ValueError(f"不支持的报告格式: {fmt}")

    # ------------------------------------------------------------------
    # PDF export with multi-engine fallback
    # ------------------------------------------------------------------

    def _save_pdf_with_fallback(self, data: ReportData, path: Path) -> dict[str, Any]:
        """Try weasyprint → pdfkit → xhtml2pdf → HTML fallback."""
        html_content = self.generate_html(data)

        # Priority 1: weasyprint
        try:
            from weasyprint import HTML as WeasyprintHTML  # noqa: PLC0415
            WeasyprintHTML(string=html_content).write_pdf(str(path))
            return {
                "success": True,
                "path": str(path),
                "actual_fmt": "pdf",
                "engine": "weasyprint",
                "message": "",
            }
        except ImportError:
            pass
        except Exception:
            # weasyprint installed but failed (e.g. missing system libs)
            pass

        # Priority 2: pdfkit (needs wkhtmltopdf binary)
        try:
            import pdfkit  # noqa: PLC0415
            pdfkit.from_string(html_content, str(path))
            return {
                "success": True,
                "path": str(path),
                "actual_fmt": "pdf",
                "engine": "pdfkit",
                "message": "",
            }
        except ImportError:
            pass
        except Exception:
            pass

        # Priority 3: xhtml2pdf (pure Python)
        try:
            from xhtml2pdf import pisa  # noqa: PLC0415
            with open(path, "wb") as f:
                pisa.CreatePDF(html_content, f)
            if path.stat().st_size > 0:
                return {
                    "success": True,
                    "path": str(path),
                    "actual_fmt": "pdf",
                    "engine": "xhtml2pdf",
                    "message": "",
                }
        except ImportError:
            pass
        except Exception:
            pass

        # Fallback: save as HTML
        fallback_path = path.with_suffix(".html")
        fallback_path.write_text(html_content, encoding="utf-8")
        return {
            "success": False,
            "path": str(fallback_path),
            "actual_fmt": "html",
            "engine": "fallback",
            "message": (
                "PDF engine not installed. Saved as HTML instead. "
                "Install PDF support: pip install weasyprint"
            ),
        }


def report_from_correction(report: dict[str, Any], input_file: str = "", output_file: str = "") -> ReportData:
    """Convert a correction report dict to ReportData."""
    return ReportData(
        input_file=input_file,
        output_file=output_file,
        template_used=report.get("template_used", ""),
        processing_time=report.get("processing_time", 0),
        quality_score=report.get("quality_score", 0),
        applied={
            "paragraphs": report.get("paragraphs_corrected", 0),
            "headings": report.get("headings_fixed", 0),
            "body": report.get("body_fixed", 0),
            "tables": report.get("tables_formatted", 0),
            "images": report.get("images_centered", 0),
        },
        skipped=report.get("skipped_items", []),
        warnings=report.get("warnings", []),
        risk_items=report.get("risk_items", []),
        rule_sources=report.get("rule_sources", {}),
        total_elements=report.get("total_elements", 0),
        modified_elements=report.get("modified_elements", 0),
        citation_issues=report.get("citation_issues"),
    )
