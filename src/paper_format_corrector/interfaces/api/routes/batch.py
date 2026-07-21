"""Batch document correction endpoint.

POST /api/v1/batch — upload multiple files, returns zip download.
"""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

router = APIRouter(tags=["batch"])

# Track temp zip files for cleanup on shutdown
_pending_zips: list[str] = []


def _cleanup_zips() -> None:
    for p in _pending_zips:
        try:
            os.unlink(p)
        except OSError:
            pass
    _pending_zips.clear()


atexit.register(_cleanup_zips)


@router.post(
    "/api/v1/batch",
    summary="批量文档矫正",
    description=(
        "上传多个 .docx 文件进行批量矫正。返回包含所有矫正结果和汇总报告的 zip 压缩包。"
        "支持指定预设模板（如 ieee, nature, apa, chinese_thesis）。"
    ),
    responses={
        200: {
            "description": "zip 压缩包，包含矫正后的文件和 batch_summary.txt",
            "content": {"application/zip": {}},
        },
        400: {"description": "没有有效的 .docx 文件"},
    },
)
async def batch_correct(
    files: list[UploadFile] = File(..., description="待矫正的 .docx 文件列表"),
    preset: str | None = Form(None, description="预设模板 ID (如 ieee, apa)"),
) -> FileResponse:
    if not files:
        raise HTTPException(status_code=400, detail="请上传至少一个文件")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        input_paths: list[str] = []

        for f in files:
            if not f.filename or not f.filename.lower().endswith(".docx"):
                continue
            file_path = tmp_path / f.filename
            content = await f.read()
            file_path.write_bytes(content)
            input_paths.append(str(file_path))

        if not input_paths:
            raise HTTPException(status_code=400, detail="没有有效的 .docx 文件")

        try:
            from paper_format_corrector.application.services.batch_service import (
                BatchCorrectionService,
            )

            config: dict[str, Any] = {}
            if preset:
                from paper_format_corrector.infra.preset_loader import load_preset

                config = load_preset(preset)

            output_dir = tmp_path / "output"
            output_dir.mkdir()

            service = BatchCorrectionService(config)
            summary = service.process_files(input_paths, output_dir)

            # Build zip inside tmp_dir
            zip_path = tmp_path / "batch_results.zip"
            with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
                for result in summary.results:
                    if result.success and Path(result.output_file).exists():
                        zf.write(result.output_file, Path(result.output_file).name)
                zf.writestr("batch_summary.txt", summary.generate_report(fmt="text"))
                zf.writestr("batch_summary.md", summary.generate_report(fmt="markdown"))

            # Copy zip to a persistent temp file so it survives tmp_dir cleanup
            persistent = tempfile.NamedTemporaryFile(
                suffix=".zip", prefix="batch_", delete=False
            )
            persistent.close()
            shutil.copy2(str(zip_path), persistent.name)
            _pending_zips.append(persistent.name)

            return FileResponse(
                path=persistent.name,
                filename="batch_results.zip",
                media_type="application/zip",
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"批量处理失败: {exc}")
