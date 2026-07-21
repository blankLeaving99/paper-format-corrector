"""任务队列管理器

提供任务提交、状态查询、持久化存储功能。
任务状态: pending → processing → completed/failed
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class Task:
    """任务数据模型"""

    id: str
    status: str  # pending | processing | completed | failed
    file_path: str
    template_id: str | None
    created_at: datetime
    updated_at: datetime
    result_path: str | None = None
    error: str | None = None
    progress: int = 0  # 0-100
    filename: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于JSON序列化）"""
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        d["updated_at"] = self.updated_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        """从字典创建Task实例"""
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)


class TaskQueue:
    """任务队列管理器

    提供线程安全的任务提交、状态查询和持久化存储。
    支持任务恢复：重启服务后可自动加载未完成的任务。
    """

    def __init__(self, storage_dir: str = "./tasks") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.queue: Queue[str] = Queue()
        self.tasks: dict[str, Task] = {}
        self._progress_callbacks: dict[str, Callable[[int], None]] = {}

        # 启动时加载未完成的任务
        self._load_pending_tasks()

    def submit(self, file_path: str, template_id: str | None = None, filename: str = "") -> str:
        """提交新任务

        Args:
            file_path: 待处理文件路径
            template_id: 模板ID（可选）
            filename: 原始文件名

        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        now = datetime.now()
        task = Task(
            id=task_id,
            status="pending",
            file_path=file_path,
            template_id=template_id,
            created_at=now,
            updated_at=now,
            filename=filename or Path(file_path).name,
        )
        self.tasks[task_id] = task
        self._save_task(task)
        self.queue.put(task_id)

        logger.info(f"任务已提交: {task_id}, 文件: {filename}")
        return task_id

    def get_status(self, task_id: str) -> dict[str, Any]:
        """获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态字典
        """
        task = self.tasks.get(task_id)
        if not task:
            return {"error": "Task not found"}
        return {
            "task_id": task.id,
            "status": task.status,
            "progress": task.progress,
            "result_path": task.result_path,
            "error": task.error,
            "filename": task.filename,
            "message": self._get_status_message(task),
        }

    def update_task(
        self,
        task_id: str,
        status: str | None = None,
        progress: int | None = None,
        result_path: str | None = None,
        error: str | None = None,
    ) -> None:
        """更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态
            progress: 进度 (0-100)
            result_path: 结果文件路径
            error: 错误信息
        """
        task = self.tasks.get(task_id)
        if not task:
            return

        if status is not None:
            task.status = status
        if progress is not None:
            task.progress = progress
        if result_path is not None:
            task.result_path = result_path
        if error is not None:
            task.error = error
        task.updated_at = datetime.now()

        self._save_task(task)

        # 触发进度回调
        callback = self._progress_callbacks.get(task_id)
        if callback and progress is not None:
            try:
                callback(progress)
            except Exception as e:
                logger.warning(f"进度回调执行失败: {e}")

    def register_progress_callback(self, task_id: str, callback: Callable[[int], None]) -> None:
        """注册进度回调

        Args:
            task_id: 任务ID
            callback: 进度回调函数
        """
        self._progress_callbacks[task_id] = callback

    def remove_task(self, task_id: str) -> None:
        """移除任务

        Args:
            task_id: 任务ID
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._progress_callbacks.pop(task_id, None)
            # 删除持久化文件
            task_file = self.storage_dir / f"{task_id}.json"
            if task_file.exists():
                task_file.unlink()

    def get_task(self, task_id: str) -> Task | None:
        """获取任务对象

        Args:
            task_id: 任务ID

        Returns:
            Task对象或None
        """
        return self.tasks.get(task_id)

    def _save_task(self, task: Task) -> None:
        """持久化任务到文件"""
        try:
            task_file = self.storage_dir / f"{task.id}.json"
            with open(task_file, "w", encoding="utf-8") as f:
                json.dump(task.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"任务持久化失败: {e}")

    def _load_pending_tasks(self) -> None:
        """启动时加载未完成的任务"""
        loaded_count = 0
        for json_file in self.storage_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                task = Task.from_dict(data)

                if task.status in ("pending", "processing"):
                    # 重置为待处理状态
                    task.status = "pending"
                    task.progress = 0
                    self.tasks[task.id] = task
                    self.queue.put(task.id)
                    loaded_count += 1
                elif task.status in ("completed", "failed"):
                    # 保留已完成/失败的任务用于查询
                    self.tasks[task.id] = task
            except Exception as e:
                logger.warning(f"加载任务文件失败 {json_file.name}: {e}")

        if loaded_count > 0:
            logger.info(f"已加载 {loaded_count} 个未完成任务")

    def _get_status_message(self, task: Task) -> str:
        """根据任务状态生成提示消息"""
        messages = {
            "pending": "任务排队中",
            "processing": f"正在处理中... ({task.progress}%)",
            "completed": "处理完成",
            "failed": f"处理失败: {task.error}" if task.error else "处理失败",
        }
        return messages.get(task.status, "未知状态")
