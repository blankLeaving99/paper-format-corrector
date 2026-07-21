"""Template validation service.

Checks template files for rule completeness and missing required fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ValidationResult:
    """Result of template validation"""
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class TemplateValidationService:
    """Validate template files for completeness and correctness."""

    REQUIRED_SECTIONS = [
        "font", "headings", "body_text", "margins", "abstract"
    ]

    REQUIRED_HEADING_LEVELS = ["heading1", "heading2", "heading3"]

    REQUIRED_FONT_FIELDS = ["chinese", "english"]

    REQUIRED_MARGIN_FIELDS = ["top", "bottom", "left", "right"]

    def validate_config(self, config: dict[str, Any]) -> ValidationResult:
        """Validate a configuration dictionary for completeness.

        Args:
            config: Configuration dictionary to validate

        Returns:
            ValidationResult with errors, warnings, and suggestions
        """
        result = ValidationResult()

        # Check top-level sections
        format_rules = config.get("format_rules", {})
        if not format_rules:
            result.errors.append("缺少 format_rules 配置节")
            result.is_valid = False
            return result

        # Validate each required section
        for section in self.REQUIRED_SECTIONS:
            if section not in format_rules:
                result.missing_fields.append(f"format_rules.{section}")
                result.errors.append(f"缺少必需配置节: {section}")
                result.is_valid = False

        # Validate font section
        if "font" in format_rules:
            self._validate_font(format_rules["font"], result)

        # Validate headings section
        if "headings" in format_rules:
            self._validate_headings(format_rules["headings"], result)

        # Validate margins section
        if "margins" in format_rules:
            self._validate_margins(format_rules["margins"], result)

        # Validate body_text section
        if "body_text" in format_rules:
            self._validate_body_text(format_rules["body_text"], result)

        # Add suggestions for optional fields
        self._add_suggestions(format_rules, result)

        return result

    def _validate_font(self, font_config: dict[str, Any], result: ValidationResult):
        """Validate font configuration."""
        for field_name in self.REQUIRED_FONT_FIELDS:
            if field_name not in font_config:
                result.warnings.append(f"字体配置缺少: {field_name}")

        # Check for heading font
        if "heading_chinese" not in font_config:
            result.suggestions.append("建议添加 heading_chinese 字体配置")

    def _validate_headings(self, headings_config: dict[str, Any], result: ValidationResult):
        """Validate headings configuration."""
        for level in self.REQUIRED_HEADING_LEVELS:
            if level not in headings_config:
                result.missing_fields.append(f"format_rules.headings.{level}")
                result.errors.append(f"缺少标题级别配置: {level}")
                result.is_valid = False
            else:
                level_config = headings_config[level]
                required_fields = ["font_size", "bold", "align"]
                for field_name in required_fields:
                    if field_name not in level_config:
                        result.warnings.append(f"标题 {level} 缺少字段: {field_name}")

    def _validate_margins(self, margins_config: dict[str, Any], result: ValidationResult):
        """Validate margins configuration."""
        for field_name in self.REQUIRED_MARGIN_FIELDS:
            if field_name not in margins_config:
                result.missing_fields.append(f"format_rules.margins.{field_name}")
                result.errors.append(f"缺少页边距配置: {field_name}")
                result.is_valid = False
            else:
                value = margins_config[field_name]
                if not isinstance(value, (int, float)) or value < 0:
                    result.warnings.append(f"页边距 {field_name} 值无效: {value}")

    def _validate_body_text(self, body_config: dict[str, Any], result: ValidationResult):
        """Validate body text configuration."""
        required_fields = ["font_size", "line_spacing"]
        for field_name in required_fields:
            if field_name not in body_config:
                result.warnings.append(f"正文配置缺少: {field_name}")

    def _add_suggestions(self, format_rules: dict[str, Any], result: ValidationResult):
        """Add suggestions for optional but recommended fields."""
        suggestions = {
            "table": "建议添加表格格式配置 (table)",
            "image": "建议添加图片格式配置 (image)",
            "reference": "建议添加参考文献格式配置 (reference)",
            "toc": "建议添加目录格式配置 (toc)",
            "header_footer": "建议添加页眉页脚配置 (header_footer)",
        }

        for key, message in suggestions.items():
            if key not in format_rules:
                result.suggestions.append(message)

    def validate_preset_file(self, file_path: str | Path) -> ValidationResult:
        """Validate a preset YAML file.

        Args:
            file_path: Path to the YAML file

        Returns:
            ValidationResult
        """
        import yaml

        path = Path(file_path)
        if not path.exists():
            return ValidationResult(
                is_valid=False,
                errors=[f"文件不存在: {path}"]
            )

        try:
            with open(path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"YAML 解析错误: {e}"]
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"文件读取错误: {e}"]
            )

        if not isinstance(config, dict):
            return ValidationResult(
                is_valid=False,
                errors=["配置文件格式错误：根节点必须是字典"]
            )

        return self.validate_config(config)

    def generate_report(self, result: ValidationResult) -> str:
        """Generate a human-readable validation report.

        Args:
            result: ValidationResult to format

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("模板验证报告")
        lines.append("=" * 60)

        if result.is_valid:
            lines.append("\n✓ 验证通过\n")
        else:
            lines.append("\n✗ 验证失败\n")

        if result.errors:
            lines.append("错误:")
            for error in result.errors:
                lines.append(f"  ✗ {error}")
            lines.append("")

        if result.warnings:
            lines.append("警告:")
            for warning in result.warnings:
                lines.append(f"  ⚠ {warning}")
            lines.append("")

        if result.missing_fields:
            lines.append("缺失字段:")
            for field_name in result.missing_fields:
                lines.append(f"  - {field_name}")
            lines.append("")

        if result.suggestions:
            lines.append("建议:")
            for suggestion in result.suggestions:
                lines.append(f"  💡 {suggestion}")
            lines.append("")

        return "\n".join(lines)
