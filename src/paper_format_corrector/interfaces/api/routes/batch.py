"""Batch document correction endpoint.

POST /api/v1/batch — upload multiple files, async processing.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from paper_format_corrector.interfaces.api.task_manager import get_task_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["batch"])


def _run_batch_correction(
    input_paths: list[str],
    output_dir: str,
    template_id: str | None,
) -> dict[str, Any]:
    """执行批量矫正（在线程池中运行）

    Args:
        input_paths: 输入文件路径列表
        output_dir: 输出目录
        template_id: 预设模板ID

    Returns:
        处理结果字典
    """
    try:
        from paper_format_corrector.application.batch_service import (
            BatchCorrectionService,
        )

        config: dict[str, Any] = {}
        if template_id:
            from paper_format_corrector.infrastructure.preset_loader import load_preset

            config = load_preset(template_id)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        service = BatchCorrectionService(config)
        summary = service.process_files(input_paths, output_path)

        # 构建zip
        zip_path = Path(output_dir) / "batch_results.zip"
        with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
            for result in summary.results:
                if result.success and Path(result.output_file).exists():
                    zf.write(result.output_file, Path(result.output_file).name)
            zf.writestr("batch_summary.txt", summary.generate_report(fmt="text"))
            zf.writestr("batch_summary.md", summary.generate_report(fmt="markdown"))

        return {
            "success": True,
            "output_path": str(zip_path),
            "report": {
                "total_files": len(input_paths),
                "successful": sum(1 for r in summary.results if r.success),
                "failed": sum(1 for r in summary.results if not r.success),
            },
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post(
    "/api/v1/batch",
    summary="批量文档矫正",
    description=(
        "上传多个 .docx 文件进行批量矫正。返回 task_id，可通过状态接口查询进度。"
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
        400: {"description": "没有有效的 .docx 文件"},
    },
)
async def batch_correct(
    files: list[UploadFile] = File(..., description="待矫正的 .docx 文件列表"),
    preset: str | None = Form(None, description="预设模板 ID (如 ieee, apa)"),
) -> dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="请上传至少一个文件")

    # 保存上传文件到临时目录
    tmp_dir = Path(tempfile.mkdtemp())
    input_paths: list[str] = []

    for f in files:
        if not f.filename or not f.filename.lower().endswith(".docx"):
            continue
        file_path = tmp_dir / f.filename
        content = await f.read()
        file_path.write_bytes(content)
        input_paths.append(str(file_path))

    if not input_paths:
        raise HTTPException(status_code=400, detail="没有有效的 .docx 文件")

    # 输出目录
    output_dir = str(tmp_dir / "output")

    # 提交任务到线程池（立即返回）
    task_manager = get_task_manager()
    task_id = task_manager.submit(
        _run_batch_correction,
        input_paths,
        output_dir,
        preset,
        task_type="batch",
        filename=f"{len(input_paths)} files",
        template_id=preset,
    )

    return {"task_id": task_id, "status": "pending"}
