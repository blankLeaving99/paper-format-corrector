"""Document correction endpoints (async task-based).

POST /api/v1/correct                — submit correction task
GET  /api/v1/correct/status/{id}    — check task progress
GET  /api/v1/correct/download/{id}  — download corrected file
"""

from __future__ import annotations

import tempfile
import uuid
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

router = APIRouter(tags=["correct"])


# ── In-memory task store (single-worker safe) ──────────────────

class _TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class _Task:
    __slots__ = ("id", "status", "progress", "message", "output_path", "filename")

    def __init__(self, task_id: str, filename: str) -> None:
        self.id = task_id
        self.status = _TaskStatus.PENDING
        self.progress = 0
        self.message = "任务已创建"
        self.output_path: Path | None = None
        self.filename = filename

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.id,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "filename": self.filename,
        }


_tasks: dict[str, _Task] = {}


def _run_correction(task: _Task, input_path: Path, preset: str | None) -> None:
    """Run the actual correction (blocking, called in background)."""
    try:
        task.status = _TaskStatus.PROCESSING
        task.progress = 20
        task.message = "正在加载矫正引擎..."

        from paper_format_corrector.app import PaperFormatCorrector

        corrector = PaperFormatCorrector()
        if preset:
            corrector.apply_preset(preset)

        task.progress = 40
        task.message = "正在矫正文档格式..."

        output_dir = Path(tempfile.mkdtemp())
        output_path = output_dir / f"corrected_{task.filename}"
        report = corrector.corrector.correct_document(str(input_path), str(output_path))

        task.progress = 90
        task.message = "矫正完成，准备下载"

        if not output_path.exists():
            task.status = _TaskStatus.FAILED
            task.message = "矫正失败：未生成输出文件"
            return

        task.output_path = output_path
        task.progress = 100
        task.status = _TaskStatus.COMPLETED
        task.message = f"矫正完成，修正段落 {report.get('paragraphs_corrected', 0)} 个"

    except Exception as exc:
        task.status = _TaskStatus.FAILED
        task.message = f"矫正失败: {exc}"


# ── Endpoints ──────────────────────────────────────────────────


@router.post(
    "/api/v1/correct",
    summary="提交文档矫正任务",
    description=(
        "上传 .docx 文件并提交异步矫正任务。返回 task_id，可通过状态接口查询进度。"
        "支持指定预设模板（如 ieee, nature, apa, chinese_thesis）。"
    ),
    response_model=dict[str, Any],
    responses={
        202: {
            "description": "任务已接受",
            "content": {
                "application/json": {
                    "example": {
                        "task_id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "processing",
                        "message": "任务已创建",
                    }
                }
            },
        },
        400: {"description": "文件格式不支持"},
    },
)
async def submit_correction(
    file: UploadFile = File(..., description="待矫正的 .docx 文件"),
    template_id: str | None = Form(None, description="预设模板 ID (如 ieee, apa)"),
) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="仅支持 .docx 格式文件")

    task_id = str(uuid.uuid4())
    task = _Task(task_id, file.filename)
    _tasks[task_id] = task

    # Save uploaded file to temp
    tmp_dir = Path(tempfile.mkdtemp())
    input_path = tmp_dir / file.filename
    content = await file.read()
    input_path.write_bytes(content)

    # Run correction synchronously (fast enough for single docs)
    _run_correction(task, input_path, template_id)

    return task.to_dict()


@router.get(
    "/api/v1/correct/status/{task_id}",
    summary="查询矫正进度",
    description="根据 task_id 查询文档矫正任务的处理进度和状态。",
    responses={
        200: {
            "description": "任务状态",
            "content": {
                "application/json": {
                    "example": {
                        "task_id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "completed",
                        "progress": 100,
                        "message": "矫正完成",
                    }
                }
            },
        },
        404: {"description": "任务不存在"},
    },
)
def get_correction_status(task_id: str) -> dict[str, Any]:
    task = _tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return task.to_dict()


@router.get(
    "/api/v1/correct/download/{task_id}",
    summary="下载矫正结果",
    description="下载矫正后的 DOCX 文件。仅在任务状态为 completed 时可用。",
    responses={
        200: {
            "description": "矫正后的 DOCX 文件",
            "content": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}
            },
        },
        404: {"description": "任务不存在或未完成"},
    },
)
def download_corrected(task_id: str) -> FileResponse:
    task = _tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    if task.status != _TaskStatus.COMPLETED:
        raise HTTPException(
            status_code=404,
            detail=f"任务未完成，当前状态: {task.status.value}",
        )
    if task.output_path is None or not task.output_path.exists():
        raise HTTPException(status_code=404, detail="输出文件不存在")

    return FileResponse(
        path=str(task.output_path),
        filename=f"corrected_{task.filename}",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
