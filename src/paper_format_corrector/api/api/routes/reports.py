"""Processing history / reports endpoints.

GET /api/v1/reports         — list recent processing records
GET /api/v1/reports/{id}    — get single report detail
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from paper_format_corrector.adapters.storage.template_repository import TemplateRepository

router = APIRouter(tags=["reports"])


def _repo() -> TemplateRepository:
    return TemplateRepository()


@router.get(
    "/api/v1/reports",
    summary="处理历史列表",
    description="返回最近的文档处理记录列表，按时间倒序排列。",
    response_model=list[dict[str, Any]],
    responses={
        200: {
            "description": "处理记录列表",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "input_file": "paper.docx",
                            "output_file": "corrected_paper.docx",
                            "template_used": "ieee",
                            "quality_score": 85.0,
                            "total_elements": 120,
                            "modified_elements": 15,
                            "processing_time": 3.2,
                            "status": "completed",
                            "created_at": "2026-07-21T10:00:00",
                        }
                    ]
                }
            },
        }
    },
)
def list_reports(
    limit: int = Query(50, ge=1, le=500, description="返回记录数量上限"),
) -> list[dict[str, Any]]:
    repo = _repo()
    return repo.list_processing_history(limit=limit)


@router.get(
    "/api/v1/reports/{record_id}",
    summary="处理报告详情",
    description="获取指定处理记录的完整报告，包含详细的矫正信息。",
    responses={
        200: {
            "description": "报告详情",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "input_file": "paper.docx",
                        "output_file": "corrected_paper.docx",
                        "template_used": "ieee",
                        "quality_score": 85.0,
                        "status": "completed",
                        "report": {
                            "paragraphs_corrected": 15,
                            "headings_fixed": 3,
                        },
                    }
                }
            },
        },
        404: {"description": "报告不存在"},
    },
)
def get_report(record_id: int) -> dict[str, Any]:
    repo = _repo()
    record = repo.get_processing_history(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"报告不存在: {record_id}")
    return record
