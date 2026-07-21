"""Minimal task queue placeholder."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskInfo:
    task_id: str
    status: str = "pending"
    file_path: str = ""
    template_id: str = ""
    filename: str = ""
    result: Any = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "file_path": self.file_path,
            "template_id": self.template_id,
            "filename": self.filename,
            "result": self.result,
            "error": self.error,
        }


class TaskQueue:
    """Simple in-memory task queue."""

    def __init__(self) -> None:
        self.tasks: dict[str, TaskInfo] = {}

    def submit(self, file_path: str, template_id: str, filename: str) -> str:
        task_id = str(uuid.uuid4())[:8]
        self.tasks[task_id] = TaskInfo(
            task_id=task_id,
            file_path=file_path,
            template_id=template_id,
            filename=filename,
        )
        return task_id

    def get_status(self, task_id: str) -> dict[str, Any]:
        task = self.tasks.get(task_id)
        if task is None:
            return {"error": f"任务不存在: {task_id}"}
        return task.to_dict()

    def get_task(self, task_id: str) -> TaskInfo | None:
        return self.tasks.get(task_id)

    def remove_task(self, task_id: str) -> bool:
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False
