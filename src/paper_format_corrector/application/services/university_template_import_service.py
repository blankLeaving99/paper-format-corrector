"""University template import automation service.

Provides workflow for importing templates from official university sources:
1. Parse requirement documents (Word/PDF/Markdown)
2. Generate format rules
3. Validate completeness
4. Save to template library with source tracking
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ImportStep:
    """Single step in the import workflow"""
    name: str
    status: str = "pending"  # pending, running, completed, failed
    message: str = ""
    result: Any = None


@dataclass
class ImportWorkflow:
    """Complete import workflow state"""
    university: str = ""
    requirement_file: str = ""
    steps: list[ImportStep] = field(default_factory=list)
    generated_config: dict[str, Any] = field(default_factory=dict)
    validation_result: Any = None
    template_slug: str = ""
    is_complete: bool = False
    error: str = ""


class UniversityTemplateImportService:
    """Automated workflow for importing university thesis templates.

    This service orchestrates the process of:
    1. Parsing official requirement documents
    2. Generating format rules from requirements
    3. Validating rule completeness
    4. Saving to the template library
    """

    def __init__(self, template_repository=None):
        """Initialize the service.

        Args:
            template_repository: Optional TemplateRepository instance
        """
        from ...infra.template_repository import TemplateRepository
        self.repo = template_repository or TemplateRepository()

    def create_workflow(
        self,
        university: str,
        requirement_file: str | Path,
    ) -> ImportWorkflow:
        """Create a new import workflow.

        Args:
            university: University name
            requirement_file: Path to requirement document

        Returns:
            ImportWorkflow with initial steps
        """
        workflow = ImportWorkflow(
            university=university,
            requirement_file=str(requirement_file),
            steps=[
                ImportStep(name="parse_requirement", message="解析需求文档"),
                ImportStep(name="generate_config", message="生成格式配置"),
                ImportStep(name="validate_config", message="验证配置完整性"),
                ImportStep(name="save_template", message="保存到模板库"),
            ],
        )
        return workflow

    def execute_workflow(self, workflow: ImportWorkflow) -> ImportWorkflow:
        """Execute the complete import workflow.

        Args:
            workflow: ImportWorkflow to execute

        Returns:
            Updated ImportWorkflow with results
        """
        try:
            # Step 1: Parse requirement document
            workflow = self._step_parse_requirement(workflow)
            if workflow.error:
                return workflow

            # Step 2: Generate config
            workflow = self._step_generate_config(workflow)
            if workflow.error:
                return workflow

            # Step 3: Validate config
            workflow = self._step_validate_config(workflow)
            if workflow.error:
                return workflow

            # Step 4: Save template
            workflow = self._step_save_template(workflow)
            if workflow.error:
                return workflow

            workflow.is_complete = True

        except Exception as e:
            workflow.error = f"工作流执行失败: {e}"

        return workflow

    def _step_parse_requirement(self, workflow: ImportWorkflow) -> ImportWorkflow:
        """Step 1: Parse the requirement document."""
        step = workflow.steps[0]
        step.status = "running"

        try:
            from ..parsers.requirement_parser import RequirementParser

            req_path = Path(workflow.requirement_file)
            if not req_path.exists():
                step.status = "failed"
                step.message = f"文件不存在: {req_path}"
                workflow.error = step.message
                return workflow

            parser = RequirementParser()
            parsed = parser.parse(str(req_path))

            step.status = "completed"
            step.result = parsed
            step.message = f"成功解析 {len(parsed)} 条规则"

        except Exception as e:
            step.status = "failed"
            step.message = f"解析失败: {e}"
            workflow.error = step.message

        return workflow

    def _step_generate_config(self, workflow: ImportWorkflow) -> ImportWorkflow:
        """Step 2: Generate format configuration from parsed requirements."""
        step = workflow.steps[1]
        step.status = "running"

        try:
            parsed = workflow.steps[0].result
            if not parsed:
                step.status = "failed"
                step.message = "无解析结果可生成配置"
                workflow.error = step.message
                return workflow

            # Build config from parsed requirements
            config = {
                "description": f"{workflow.university} 毕业论文格式模板",
                "format_rules": {
                    "font": {
                        "chinese": "宋体",
                        "english": "Times New Roman",
                        "heading_chinese": "黑体",
                    },
                    "headings": {
                        "heading1": {
                            "font_size": 16,
                            "bold": True,
                            "align": "center",
                            "space_before": 24,
                            "space_after": 12,
                            "line_spacing": 1.5,
                        },
                        "heading2": {
                            "font_size": 14,
                            "bold": True,
                            "align": "left",
                            "space_before": 18,
                            "space_after": 8,
                            "line_spacing": 1.5,
                        },
                        "heading3": {
                            "font_size": 12,
                            "bold": True,
                            "align": "left",
                            "space_before": 12,
                            "space_after": 6,
                            "line_spacing": 1.5,
                        },
                    },
                    "body_text": {
                        "font_size": 12,
                        "line_spacing": 1.5,
                        "first_line_indent": 2,
                        "align": "justify",
                    },
                    "margins": {
                        "top": 3.0,
                        "bottom": 3.0,
                        "left": 2.5,
                        "right": 2.5,
                    },
                    "abstract": {
                        "title_font_size": 14,
                        "title_bold": True,
                        "title_align": "center",
                        "font_size": 12,
                        "line_spacing": 1.5,
                        "max_lines": 500,
                    },
                },
                "auto_detect": {
                    "title": {"patterns": ["题目", "标题"], "confidence": 0.9},
                    "author": {"patterns": ["作者", "学生姓名"], "confidence": 0.9},
                    "abstract": {"patterns": ["摘要", "摘要："], "confidence": 0.95},
                    "keywords": {"patterns": ["关键词", "关键词："], "confidence": 0.9},
                    "reference": {"patterns": ["参考文献"], "confidence": 0.95},
                },
            }

            # Apply parsed rules to config
            if isinstance(parsed, dict):
                for key, value in parsed.items():
                    if key in config["format_rules"]:
                        if isinstance(config["format_rules"][key], dict):
                            config["format_rules"][key].update(value)
                        else:
                            config["format_rules"][key] = value

            workflow.generated_config = config
            step.status = "completed"
            step.result = config
            step.message = "配置生成成功"

        except Exception as e:
            step.status = "failed"
            step.message = f"配置生成失败: {e}"
            workflow.error = step.message

        return workflow

    def _step_validate_config(self, workflow: ImportWorkflow) -> ImportWorkflow:
        """Step 3: Validate the generated configuration."""
        step = workflow.steps[2]
        step.status = "running"

        try:
            from ..application.services.template_validation_service import TemplateValidationService

            service = TemplateValidationService()
            result = service.validate_config(workflow.generated_config)

            workflow.validation_result = result
            step.status = "completed"
            step.result = result
            step.message = f"验证{'通过' if result.is_valid else '失败'}"

            if not result.is_valid:
                workflow.error = f"配置验证失败: {'; '.join(result.errors)}"

        except Exception as e:
            step.status = "failed"
            step.message = f"验证失败: {e}"
            workflow.error = step.message

        return workflow

    def _step_save_template(self, workflow: ImportWorkflow) -> ImportWorkflow:
        """Step 4: Save the template to the database."""
        step = workflow.steps[3]
        step.status = "running"

        try:
            # Generate slug from university name
            slug = self._generate_slug(workflow.university)

            # Calculate source file hash
            req_path = Path(workflow.requirement_file)
            file_hash = self._file_hash(req_path) if req_path.exists() else ""

            # Save to repository
            saved = self.repo.save_personal_template(
                name=f"{workflow.university} 毕业论文模板",
                category="高校毕业论文",
                config=workflow.generated_config,
            )

            workflow.template_slug = saved.slug if hasattr(saved, "slug") else slug
            step.status = "completed"
            step.result = workflow.template_slug
            step.message = f"模板已保存: {workflow.template_slug}"

        except Exception as e:
            step.status = "failed"
            step.message = f"保存失败: {e}"
            workflow.error = step.message

        return workflow

    def _generate_slug(self, name: str) -> str:
        """Generate a URL-safe slug from a name."""
        import re
        slug = name.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')

    def _file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def get_workflow_status(self, workflow: ImportWorkflow) -> dict:
        """Get current workflow status.

        Args:
            workflow: ImportWorkflow to check

        Returns:
            Status dictionary
        """
        completed = sum(1 for s in workflow.steps if s.status == "completed")
        total = len(workflow.steps)

        return {
            "university": workflow.university,
            "requirement_file": workflow.requirement_file,
            "progress": f"{completed}/{total}",
            "is_complete": workflow.is_complete,
            "error": workflow.error,
            "steps": [
                {
                    "name": s.name,
                    "status": s.status,
                    "message": s.message,
                }
                for s in workflow.steps
            ],
        }
