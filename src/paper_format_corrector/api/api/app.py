"""REST API server for paper format correction.

Provides HTTP endpoints for document correction, batch processing,
template management, and report generation.

Usage:
    python -m paper_format_corrector.api.app
    # or
    uvicorn paper_format_corrector.api.app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from ...app import PaperFormatCorrector
from ...services.batch_service import BatchCorrectionService
from ...services.report_service import ReportService
from ...services.style_workbench import (
    build_correction_plan,
    explain_style_profile,
    learn_style_profile,
    scan_document,
)
from ...adapters.preset_loader import list_presets
from ...adapters.storage.template_repository import TemplateRepository
from ...adapters.queue.task_queue import TaskQueue
from ...adapters.queue.worker import Worker

app = FastAPI(
    title="论文格式矫正 API",
    description="Paper Format Correction Service - 自动矫正论文格式",
    version="1.0.0",
)

# Temp dir tracking
_temp_dirs: list[str] = []

# Task queue (lazy-initialized singleton)
_task_queue: TaskQueue | None = None
_worker: Worker | None = None


def get_task_queue() -> TaskQueue:
    """获取或创建全局任务队列实例，并确保 Worker 已启动。"""
    global _task_queue, _worker
    if _task_queue is None:
        _task_queue = TaskQueue()
        _worker = Worker(_task_queue, num_workers=2)
        _worker.start()
    return _task_queue


# ── Include modular routers (api/v1) ───────────────────────────
from .routes.health import router as health_router
from .routes.templates import router as templates_router
from .routes.correct import router as correct_router
from .routes.scan import router as scan_router
from .routes.batch import router as batch_router
from .routes.reports import router as reports_router

app.include_router(health_router)
app.include_router(templates_router)
app.include_router(correct_router)
app.include_router(scan_router)
app.include_router(batch_router)
app.include_router(reports_router)


# ── Root ───────────────────────────────────────────────────────


@app.get("/")
def root():
    return {
        "service": "paper-format-correction",
        "version": "1.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


# ── Request/Response Models ────────────────────────────────────


class CorrectRequest(BaseModel):
    preset: str | None = None
    config: dict[str, Any] | None = None


class ScanResponse(BaseModel):
    elements: dict[str, int]
    margins: dict[str, float]
    confidence: list[dict[str, Any]]
    page_setup: dict[str, Any]


class PlanResponse(BaseModel):
    total_affected: int
    items: list[dict[str, Any]]
    risk_items: list[dict[str, Any]]


class TemplateCreateRequest(BaseModel):
    name: str
    category: str
    config: dict[str, Any]


class TemplateSearchRequest(BaseModel):
    keyword: str
    category: str | None = None


# ── Health ─────────────────────────────────────────────────────


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "paper-format-correction"}


# ── Document Correction ────────────────────────────────────────


@app.post("/correct")
async def correct_document(
    file: UploadFile = File(...),
    preset: str | None = None,
):
    """矫正单个论文文档。

    Args:
        file: 上传的 .docx 文件
        preset: 预设模板名称（如 ieee, apa 等）
    """
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(400, "仅支持 .docx 格式文件")

    with tempfile.TemporaryDirectory() as tmp_dir:
        input_path = Path(tmp_dir) / file.filename
        output_path = Path(tmp_dir) / f"corrected_{file.filename}"

        content = await file.read()
        input_path.write_bytes(content)

        try:
            corrector = PaperFormatCorrector()
            if preset:
                corrector.apply_preset(preset)
            report = corrector.corrector.correct_document(str(input_path), str(output_path))

            if not output_path.exists():
                raise HTTPException(500, "矫正失败，未生成输出文件")

            return FileResponse(
                path=str(output_path),
                filename=f"corrected_{file.filename}",
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"X-Correction-Report": str(report)},
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(500, f"矫正失败: {exc}")


@app.post("/scan")
async def scan_document_structure(file: UploadFile = File(...)):
    """扫描文档结构，返回元素类型、数量和置信度。"""
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(400, "仅支持 .docx 格式文件")

    with tempfile.TemporaryDirectory() as tmp_dir:
        input_path = Path(tmp_dir) / file.filename
        content = await file.read()
        input_path.write_bytes(content)

        try:
            result = scan_document(str(input_path))
            return result
        except Exception as exc:
            raise HTTPException(500, f"扫描失败: {exc}")


@app.post("/plan")
async def generate_correction_plan(
    file: UploadFile = File(...),
    preset: str | None = None,
):
    """生成矫正计划（dry-run），不实际修改文件。"""
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(400, "仅支持 .docx 格式文件")

    with tempfile.TemporaryDirectory() as tmp_dir:
        input_path = Path(tmp_dir) / file.filename
        content = await file.read()
        input_path.write_bytes(content)

        try:
            config: dict[str, Any] = {}
            if preset:
                from ..adapters.preset_loader import load_preset
                config = load_preset(preset)

            format_rules = config.get("format_rules", {})
            plan = build_correction_plan(str(input_path), format_rules)

            from ..services.style_workbench import plan_to_dict
            return plan_to_dict(plan)
        except Exception as exc:
            raise HTTPException(500, f"生成计划失败: {exc}")


@app.post("/learn")
async def learn_from_sample(file: UploadFile = File(...)):
    """从样本文档学习格式规则。支持 .docx 和 .pdf 格式。"""
    if not file.filename:
        raise HTTPException(400, "未提供文件名")
    ext = file.filename.lower().rsplit(".", 1)[-1] if "." in file.filename else ""
    if ext not in ("docx", "pdf"):
        raise HTTPException(400, "仅支持 .docx 和 .pdf 格式文件")

    with tempfile.TemporaryDirectory() as tmp_dir:
        input_path = Path(tmp_dir) / file.filename
        content = await file.read()
        input_path.write_bytes(content)

        try:
            if ext == "pdf":
                # PDF 反向学习
                try:
                    from ..core.document.pdf_style_extractor import PDFStyleExtractor
                    extractor = PDFStyleExtractor(str(input_path))
                    profile = extractor.extract_style_profile()
                    return {"profile": profile, "source_format": "pdf"}
                except ImportError:
                    raise HTTPException(400, "PDF 学习功能需要安装 pdfplumber: pip install pdfplumber")
            else:
                profile = learn_style_profile(str(input_path))
                explanation = explain_style_profile(str(input_path))
                return {"profile": profile, "explanation": explanation}
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(500, f"学习失败: {exc}")


# ── Batch Processing ───────────────────────────────────────────


@app.post("/batch")
async def batch_correct(
    files: list[UploadFile] = File(...),
    preset: str | None = None,
):
    """批量矫正多个论文文档，返回 zip 压缩包。"""
    if not files:
        raise HTTPException(400, "请上传至少一个文件")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        input_paths = []

        for f in files:
            if not f.filename or not f.filename.lower().endswith(".docx"):
                continue
            file_path = tmp_path / f.filename
            content = await f.read()
            file_path.write_bytes(content)
            input_paths.append(str(file_path))

        if not input_paths:
            raise HTTPException(400, "没有有效的 .docx 文件")

        try:
            config: dict[str, Any] = {}
            if preset:
                from ..adapters.preset_loader import load_preset
                config = load_preset(preset)

            output_dir = tmp_path / "output"
            output_dir.mkdir()

            service = BatchCorrectionService(config)
            summary = service.process_files(input_paths, output_dir)

            # Create zip
            zip_path = tmp_path / "batch_results.zip"
            with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
                for result in summary.results:
                    if result.success and Path(result.output_file).exists():
                        zf.write(result.output_file, Path(result.output_file).name)
                # Add summary report
                report_text = summary.generate_report(fmt="text")
                zf.writestr("batch_summary.txt", report_text)
                report_md = summary.generate_report(fmt="markdown")
                zf.writestr("batch_summary.md", report_md)

            return FileResponse(
                path=str(zip_path),
                filename="batch_results.zip",
                media_type="application/zip",
            )
        except Exception as exc:
            raise HTTPException(500, f"批量处理失败: {exc}")


# ── Templates ──────────────────────────────────────────────────


@app.get("/templates")
def list_templates(category: str | None = None, keyword: str | None = None):
    """列出模板库中的模板。"""
    repo = TemplateRepository()
    if keyword:
        templates = repo.search_templates(keyword)
    else:
        templates = repo.list_templates(category=category)
    return [
        {
            "slug": t.slug,
            "name": t.name,
            "category": t.category,
            "source": t.source,
            "organization": t.organization,
            "version": t.version,
            "is_active": t.is_active,
            "tags": t.tags,
        }
        for t in templates
    ]


@app.get("/templates/{slug}")
def get_template(slug: str):
    """获取模板详情。"""
    repo = TemplateRepository()
    record = repo.get(slug)
    if record is None:
        raise HTTPException(404, f"模板不存在: {slug}")
    tags = repo.get(slug)
    return {
        "slug": record.slug,
        "name": record.name,
        "category": record.category,
        "source": record.source,
        "organization": record.organization,
        "degree_level": record.degree_level,
        "discipline": record.discipline,
        "language": record.language,
        "version": record.version,
        "tags": record.tags,
        "description": record.description,
        "config": record.config,
        "is_active": record.is_active,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


@app.post("/templates")
def create_template(req: TemplateCreateRequest):
    """创建个人模板。"""
    repo = TemplateRepository()
    try:
        saved = repo.save_personal_template(req.name, req.category, req.config)
        return {"slug": saved.slug, "name": saved.name, "message": "创建成功"}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@app.delete("/templates/{slug}")
def delete_template(slug: str):
    """删除模板（内置模板仅禁用）。"""
    repo = TemplateRepository()
    success = repo.delete_template(slug)
    if not success:
        raise HTTPException(404, f"模板不存在: {slug}")
    return {"message": f"模板 {slug} 已删除"}


@app.get("/templates/{slug}/export")
def export_template(slug: str, format: str = "yaml"):
    """导出模板为 YAML 或 JSON。"""
    repo = TemplateRepository()
    record = repo.get(slug)
    if record is None:
        raise HTTPException(404, f"模板不存在: {slug}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = Path(tmp_dir) / f"template_{slug}.{format}"
        try:
            if format == "yaml":
                repo.export_to_yaml(slug, str(output_path))
            else:
                repo.export_to_json(slug, str(output_path))
            return FileResponse(
                path=str(output_path),
                filename=f"template_{slug}.{format}",
                media_type="application/octet-stream",
            )
        except Exception as exc:
            raise HTTPException(500, str(exc))


@app.get("/templates/{slug}/summary")
def get_template_summary(slug: str):
    """获取模板样式摘要。"""
    repo = TemplateRepository()
    summary = repo.get_template_summary(slug)
    if summary is None:
        raise HTTPException(404, f"模板不存在: {slug}")
    return summary


@app.get("/templates/categories/list")
def list_categories():
    """列出所有分类及数量。"""
    repo = TemplateRepository()
    return repo.list_categories()


@app.get("/templates/organizations/list")
def list_organizations():
    """列出所有组织及数量。"""
    repo = TemplateRepository()
    return repo.list_organizations()


@app.get("/templates/tags/list")
def list_tags():
    """列出所有标签及使用次数。"""
    repo = TemplateRepository()
    return repo.list_tags()


@app.post("/templates/validate")
def validate_template_config(config: dict):
    """验证模板配置的完整性和正确性。"""
    from ..services.template_validation_service import TemplateValidationService
    service = TemplateValidationService()
    result = service.validate_config(config)
    return {
        "is_valid": result.is_valid,
        "errors": result.errors,
        "warnings": result.warnings,
        "missing_fields": result.missing_fields,
        "suggestions": result.suggestions,
    }


# ── University Template Import ─────────────────────────────────


@app.post("/university-import/start")
def start_university_import(university: str, requirement_file: str):
    """启动高校模板自动导入工作流。

    Args:
        university: 高校名称
        requirement_file: 需求文档路径
    """
    from ..services.university_template_import_service import UniversityTemplateImportService
    service = UniversityTemplateImportService()
    workflow = service.create_workflow(university, requirement_file)
    workflow = service.execute_workflow(workflow)
    return service.get_workflow_status(workflow)


@app.get("/university-import/status")
def get_import_status(workflow_id: str | None = None):
    """获取导入工作流状态。"""
    return {"message": "请使用 /university-import/start 启动新工作流"}


# ── Presets ────────────────────────────────────────────────────


@app.get("/presets")
def list_presets_api():
    """列出所有内置预设模板。"""
    return list_presets()


# ── Reports ────────────────────────────────────────────────────


@app.get("/reports")
def list_reports(limit: int = 50):
    """列出历史处理报告。"""
    repo = TemplateRepository()
    return repo.list_processing_history(limit=limit)


@app.get("/reports/{record_id}")
def get_report(record_id: int):
    """获取单条报告详情。"""
    repo = TemplateRepository()
    record = repo.get_processing_history(record_id)
    if record is None:
        raise HTTPException(404, f"报告不存在: {record_id}")
    return record


# ── Task Queue ────────────────────────────────────────────────


class TaskSubmitRequest(BaseModel):
    file_path: str
    template_id: str | None = None
    filename: str = ""


@app.post("/tasks/submit")
def submit_task(req: TaskSubmitRequest):
    """提交文档矫正任务到队列，返回任务 ID 用于后续状态轮询。"""
    queue = get_task_queue()
    task_id = queue.submit(req.file_path, req.template_id, req.filename)
    return {"task_id": task_id, "status": "pending"}


@app.get("/tasks/{task_id}")
def get_task_status(task_id: str):
    """查询单个任务的状态和进度。"""
    queue = get_task_queue()
    status = queue.get_status(task_id)
    if "error" in status:
        raise HTTPException(404, status["error"])
    return status


@app.get("/tasks")
def list_tasks(status: str | None = None, limit: int = 50):
    """列出所有任务，可按状态过滤。"""
    queue = get_task_queue()
    tasks = list(queue.tasks.values())
    if status:
        tasks = [t for t in tasks if t.status == status]
    tasks = tasks[:limit]
    return {
        "total": len(tasks),
        "tasks": [t.to_dict() for t in tasks],
    }


@app.delete("/tasks/{task_id}")
def remove_task(task_id: str):
    """移除已完成或失败的任务。"""
    queue = get_task_queue()
    task = queue.get_task(task_id)
    if task is None:
        raise HTTPException(404, f"任务不存在: {task_id}")
    if task.status in ("pending", "processing"):
        raise HTTPException(400, "无法删除进行中的任务")
    queue.remove_task(task_id)
    return {"message": f"任务 {task_id} 已删除"}


@app.get("/tasks/{task_id}/result")
def get_task_result(task_id: str):
    """获取已完成任务的结果文件。"""
    queue = get_task_queue()
    task = queue.get_task(task_id)
    if task is None:
        raise HTTPException(404, f"任务不存在: {task_id}")
    if task.status != "completed":
        raise HTTPException(400, f"任务尚未完成，当前状态: {task.status}")
    if not task.result_path or not Path(task.result_path).exists():
        raise HTTPException(404, "结果文件不存在")
    return FileResponse(
        path=task.result_path,
        filename=task.filename or "corrected.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


# ── LaTeX Export ─────────────────────────────────────────────────


@app.post("/export/latex")
async def export_latex(file: UploadFile = File(...)):
    """将 DOCX 文档导出为 LaTeX (.tex) 格式。"""
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(400, "仅支持 .docx 格式文件")

    with tempfile.TemporaryDirectory() as tmp_dir:
        input_path = Path(tmp_dir) / file.filename
        content = await file.read()
        input_path.write_bytes(content)

        output_path = Path(tmp_dir) / f"{input_path.stem}.tex"

        try:
            from ..adapters.word.latex_exporter import LaTeXExporter
            exporter = LaTeXExporter()
            exporter.export(str(input_path), str(output_path))
            return FileResponse(
                path=str(output_path),
                filename=output_path.name,
                media_type="application/x-tex",
            )
        except ImportError:
            raise HTTPException(500, "LaTeX 导出模块不可用")
        except Exception as exc:
            raise HTTPException(500, f"LaTeX 导出失败: {exc}")


# ── Main ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
