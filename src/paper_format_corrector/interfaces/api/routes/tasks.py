"""Unified task status endpoint.

GET /api/v1/tasks/{task_id} — check any task progress
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Any

from paper_format_corrector.interfaces.api.task_manager import get_task_manager

router = APIRouter(tags=["tasks"])


@router.get(
    "/api/v1/tasks/{task_id}",
    summary="查询任务状态",
    description="根据 task_id 查询任意类型任务（矫正/批量）的处理进度和状态。",
    responses={
        200: {
            "description": "任务状态",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "completed",
                        "progress": 100,
                        "task_type": "correct",
                    }
                }
            },
        },
        404: {"description": "任务不存在"},
    },
)
def get_task_status(task_id: str) -> dict[str, Any]:
    task_manager = get_task_manager()
    status = task_manager.get_status(task_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return status
