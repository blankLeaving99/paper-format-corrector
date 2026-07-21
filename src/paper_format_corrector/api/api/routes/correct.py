"""Document correction endpoints (async task-based).

POST /api/v1/correct                — submit correction task
GET  /api/v1/correct/status/{id}    — check task progress
GET  /api/v1/correct/download/{id}  — download corrected file
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from paper_format_corrector.api.api.task_manager import get_task_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["correct"])


def _run_correction(file_path: str, template_id: str | None, filename: str) -> dict[str, Any]:
    """执行文档矫正（在线程池中运行）

    Args:
        file_path: 输入文件路径
        template_id: 预设模板ID
        filename: 原始文件名

    Returns:
        处理结果字典
    """
    try:
        from paper_format_corrector.app import PaperFormatCorrector

        corrector = PaperFormatCorrector()
        if template_id:
            corrector.apply_preset(template_id)

        output_dir = Path(tempfile.mkdtemp())
        output_path = output_dir / f"corrected_{filename}"

        report = corrector.corrector.correct_document(file_path, str(output_path))

        if not output_path.exists():
            return {"success": False, "error": "矫正失败：未生成输出文件"}

        return {
            "success": True,
            "output_path": str(output_path),
            "report": report,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


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
                        "status": "pending",
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

    # 保存上传文件到临时目录
    tmp_dir = Path(tempfile.mkdtemp())
    input_path = tmp_dir / file.filename
    content = await file.read()
    input_path.write_bytes(content)

    # 提交任务到线程池（立即返回）
    task_manager = get_task_manager()
    task_id = task_manager.submit(
        _run_correction,
        str(input_path),
        template_id,
        file.filename,
        task_type="correct",
        filename=file.filename,
        template_id=template_id,
    )

    return {"task_id": task_id, "status": "pending"}


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
                    }
                }
            },
        },
        404: {"description": "任务不存在"},
    },
)
def get_correction_status(task_id: str) -> dict[str, Any]:
    task_manager = get_task_manager()
    status = task_manager.get_status(task_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return status


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
    task_manager = get_task_manager()
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    if task.status != "completed":
        raise HTTPException(
            status_code=404,
            detail=f"任务未完成，当前状态: {task.status}",
        )
    if not task.result_path or not Path(task.result_path).exists():
        raise HTTPException(status_code=404, detail="输出文件不存在")

    return FileResponse(
        path=task.result_path,
        filename=f"corrected_{task.filename}",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
