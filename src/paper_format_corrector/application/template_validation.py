"""Template validation service.

Validates template configuration completeness and correctness
before the template is used for document correction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationIssue:
    """A single validation issue."""
    field: str
    severity: str  # "error", "warning", "info"
    message: str


@dataclass
class TemplateValidationReport:
    """Result of template validation."""
    slug: str
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    score: float = 0.0  # 0-100

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "is_valid": self.is_valid,
            "score": self.score,
            "errors": len([i for i in self.issues if i.severity == "error"]),
            "warnings": len([i for i in self.issues if i.severity == "warning"]),
            "issues": [
                {"field": i.field, "severity": i.severity, "message": i.message}
                for i in self.issues
            ],
        }


class TemplateValidationService:
    """Validates template configurations for completeness and correctness."""

    REQUIRED_SECTIONS = ["font", "body_text", "headings"]
    RECOMMENDED_SECTIONS = ["tables", "images", "margins"]
    VALID_TABLE_STYLES = {"three_line", "full_border", "keep", "apa", "ieee", "nature"}
    VALID_IMAGE_WIDTHS = {"full", "90%", "80%", "70%", "60%", "50%", "40%", "30%"}
    VALID_ALIGNMENTS = {"left", "center", "right", "justify", "both"}
    VALID_HEADING_ALIGNMENTS = {"left", "center", "right"}

    def validate(self, slug: str, config: dict[str, Any]) -> TemplateValidationReport:
        """Validate a template configuration.

        Args:
            slug: Template identifier
            config: The template config dict (should contain format_rules)

        Returns:
            TemplateValidationReport with issues and score
        """
        issues: list[ValidationIssue] = []
        format_rules = config.get("format_rules", config)

        # ── Required sections ──
        for section in self.REQUIRED_SECTIONS:
            if section not in format_rules:
                issues.append(ValidationIssue(
                    field=section,
                    severity="error",
                    message=f"缺少必要配置项: {section}",
                ))

        # ── Font section ──
        font = format_rules.get("font", {})
        if font:
            if not font.get("chinese") and not font.get("english"):
                issues.append(ValidationIssue(
                    field="font.chinese",
                    severity="warning",
                    message="未指定中文字体或英文字体",
                ))

        # ── Body text ──
        body = format_rules.get("body_text", {})
        if body:
            size = body.get("font_size")
            if size is not None:
                if not isinstance(size, (int, float)) or size < 8 or size > 24:
                    issues.append(ValidationIssue(
                        field="body_text.font_size",
                        severity="warning",
                        message=f"正文字号 {size}pt 不在常见范围 (8-24pt)",
                    ))
            spacing = body.get("line_spacing")
            if spacing is not None:
                if not isinstance(spacing, (int, float)) or spacing < 1.0 or spacing > 3.0:
                    issues.append(ValidationIssue(
                        field="body_text.line_spacing",
                        severity="warning",
                        message=f"正文行距 {spacing} 不在常见范围 (1.0-3.0)",
                    ))

        # ── Headings ──
        headings = format_rules.get("headings", {})
        if headings:
            for level in ["heading1", "heading2", "heading3"]:
                h = headings.get(level, {})
                if h:
                    h_size = h.get("font_size")
                    if h_size is not None:
                        if not isinstance(h_size, (int, float)) or h_size < 10 or h_size > 36:
                            issues.append(ValidationIssue(
                                field=f"headings.{level}.font_size",
                                severity="warning",
                                message=f"{level} 字号 {h_size}pt 不在常见范围 (10-36pt)",
                            ))
                    h_align = h.get("align")
                    if h_align and h_align not in self.VALID_HEADING_ALIGNMENTS:
                        issues.append(ValidationIssue(
                            field=f"headings.{level}.align",
                            severity="warning",
                            message=f"{level} 对齐方式 '{h_align}' 无效",
                        ))
            # Check heading hierarchy (h1 > h2 > h3)
            h1_size = headings.get("heading1", {}).get("font_size", 16)
            h2_size = headings.get("heading2", {}).get("font_size", 14)
            h3_size = headings.get("heading3", {}).get("font_size", 12)
            if isinstance(h1_size, (int, float)) and isinstance(h2_size, (int, float)):
                if h2_size >= h1_size:
                    issues.append(ValidationIssue(
                        field="headings",
                        severity="warning",
                        message=f"二级标题字号 ({h2_size}) >= 一级标题字号 ({h1_size})，层级可能颠倒",
                    ))
            if isinstance(h2_size, (int, float)) and isinstance(h3_size, (int, float)):
                if h3_size >= h2_size:
                    issues.append(ValidationIssue(
                        field="headings",
                        severity="warning",
                        message=f"三级标题字号 ({h3_size}) >= 二级标题字号 ({h2_size})，层级可能颠倒",
                    ))

        # ── Tables ──
        tables = format_rules.get("tables", {})
        if tables:
            style = tables.get("style")
            if style and style not in self.VALID_TABLE_STYLES:
                issues.append(ValidationIssue(
                    field="tables.style",
                    severity="warning",
                    message=f"表格样式 '{style}' 不在支持列表中",
                ))
            t_size = tables.get("font_size")
            if t_size is not None:
                if not isinstance(t_size, (int, float)) or t_size < 8 or t_size > 16:
                    issues.append(ValidationIssue(
                        field="tables.font_size",
                        severity="warning",
                        message=f"表格字号 {t_size}pt 不在常见范围 (8-16pt)",
                    ))

        # ── Images ──
        images = format_rules.get("images", {})
        if images:
            width = images.get("max_width")
            if width and width not in self.VALID_IMAGE_WIDTHS:
                issues.append(ValidationIssue(
                    field="images.max_width",
                    severity="warning",
                    message=f"图片宽度 '{width}' 不在支持列表中",
                ))

        # ── Margins ──
        margins = format_rules.get("margins", {})
        if margins:
            for side in ["top", "bottom", "left", "right"]:
                val = margins.get(side)
                if val is not None:
                    if not isinstance(val, (int, float)):
                        issues.append(ValidationIssue(
                            field=f"margins.{side}",
                            severity="error",
                            message=f"页边距 {side} 不是数字",
                        ))
                    elif val < 0 or val > 10:
                        issues.append(ValidationIssue(
                            field=f"margins.{side}",
                            severity="warning",
                            message=f"页边距 {side}: {val}cm 不在常见范围 (0-10cm)",
                        ))

        # ── Recommended sections ──
        for section in self.RECOMMENDED_SECTIONS:
            if section not in format_rules:
                issues.append(ValidationIssue(
                    field=section,
                    severity="info",
                    message=f"建议添加配置项: {section}",
                ))

        # Calculate score
        errors = len([i for i in issues if i.severity == "error"])
        warnings = len([i for i in issues if i.severity == "warning"])
        infos = len([i for i in issues if i.severity == "info"])
        score = max(0, 100 - errors * 20 - warnings * 5 - infos * 1)

        return TemplateValidationReport(
            slug=slug,
            is_valid=errors == 0,
            issues=issues,
            score=score,
        )
