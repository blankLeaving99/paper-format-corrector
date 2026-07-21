"""任务管理器

提供线程池执行、内存状态管理、可选JSON持久化。
"""

from __future__ import annotations

import json
import logging
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class TaskInfo:
    """任务数据模型"""

    id: str
    status: str  # pending | processing | completed | failed
    progress: int  # 0-100
    created_at: str
    updated_at: str
    file_path: str
    filename: str
    task_type: str  # correct | batch
    template_id: str | None = None
    result_path: str | None = None
    error: str | None = None
    result_data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TaskManager:
    """任务管理器

    使用ThreadPoolExecutor执行后台任务，支持：
    - 内存状态查询
    - 可选JSON文件持久化
    - 任务进度回调
    """

    def __init__(self, max_workers: int = 2, storage_dir: str | None = None) -> None:
        """初始化TaskManager

        Args:
            max_workers: 线程池最大工作线程数
            storage_dir: 持久化目录，None则仅内存存储
        """
        self.max_workers = max_workers
        self.storage_dir = Path(storage_dir) if storage_dir else None
        self.tasks: dict[str, TaskInfo] = {}
        self._lock = threading.Lock()
        self._executor: ThreadPoolExecutor | None = None

        if self.storage_dir:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self._load_pending_tasks()

    def start(self) -> None:
        """启动线程池"""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=self.max_workers,
                thread_name_prefix="task-worker",
            )
            logger.info(f"TaskManager已启动，线程池大小: {self.max_workers}")

    def stop(self) -> None:
        """停止线程池"""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
            logger.info("TaskManager已停止")

    def submit(
        self,
        func: Callable[..., Any],
        *args: Any,
        task_type: str = "correct",
        filename: str = "",
        template_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """提交任务

        Args:
            func: 要执行的函数
            *args: 函数位置参数
            task_type: 任务类型 (correct|batch)
            filename: 原始文件名
            template_id: 模板ID
            **kwargs: 函数关键字参数

        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        # 获取文件路径（从args中提取）
        file_path = ""
        if args and isinstance(args[0], (str, Path)):
            file_path = str(args[0])

        task = TaskInfo(
            id=task_id,
            status="pending",
            progress=0,
            created_at=now,
            updated_at=now,
            file_path=file_path,
            filename=filename or Path(file_path).name,
            task_type=task_type,
            template_id=template_id,
        )

        with self._lock:
            self.tasks[task_id] = task

        self._save_task(task)

        # 提交到线程池
        if self._executor is None:
            self.start()

        self._executor.submit(self._run_task, task_id, func, args, kwargs)

        logger.info(f"任务已提交: {task_id}, 类型: {task_type}")
        return task_id

    def get_task(self, task_id: str) -> TaskInfo | None:
        """获取任务信息

        Args:
            task_id: 任务ID

        Returns:
            TaskInfo或None
        """
        return self.tasks.get(task_id)

    def get_status(self, task_id: str) -> dict[str, Any]:
        """获取任务状态字典

        Args:
            task_id: 任务ID

        Returns:
            状态字典
        """
        task = self.tasks.get(task_id)
        if not task:
            return {"error": "Task not found"}
        return task.to_dict()

    def update_progress(self, task_id: str, progress: int) -> None:
        """更新任务进度

        Args:
            task_id: 任务ID
            progress: 进度 (0-100)
        """
        task = self.tasks.get(task_id)
        if task:
            task.progress = min(max(progress, 0), 100)
            task.updated_at = datetime.now().isoformat()
            self._save_task(task)

    def _run_task(
        self,
        task_id: str,
        func: Callable[..., Any],
        args: tuple,
        kwargs: dict,
    ) -> None:
        """执行任务（在工作线程中运行）

        Args:
            task_id: 任务ID
            func: 要执行的函数
            args: 位置参数
            kwargs: 关键字参数
        """
        task = self.tasks.get(task_id)
        if not task:
            return

        try:
            # 更新状态为处理中
            task.status = "processing"
            task.progress = 10
            task.updated_at = datetime.now().isoformat()
            self._save_task(task)

            logger.info(f"开始执行任务: {task_id}")

            # 执行函数
            result = func(*args, **kwargs)

            # 处理结果
            if isinstance(result, dict):
                if result.get("success"):
                    task.status = "completed"
                    task.progress = 100
                    task.result_path = result.get("output_path")
                    task.result_data = result.get("report")
                else:
                    task.status = "failed"
                    task.error = result.get("error", "未知错误")
            else:
                task.status = "completed"
                task.progress = 100
                task.result_data = result

            task.updated_at = datetime.now().isoformat()
            self._save_task(task)

            logger.info(f"任务完成: {task_id}, 状态: {task.status}")

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.updated_at = datetime.now().isoformat()
            self._save_task(task)
            logger.error(f"任务异常: {task_id}, 错误: {e}", exc_info=True)

    def _save_task(self, task: TaskInfo) -> None:
        """持久化任务到JSON文件"""
        if not self.storage_dir:
            return

        try:
            task_file = self.storage_dir / f"{task.id}.json"
            with open(task_file, "w", encoding="utf-8") as f:
                json.dump(task.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"任务持久化失败: {e}")

    def _load_pending_tasks(self) -> None:
        """启动时加载未完成的任务"""
        if not self.storage_dir:
            return

        loaded_count = 0
        for json_file in self.storage_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                task = TaskInfo(**data)

                if task.status in ("pending", "processing"):
                    task.status = "pending"
                    task.progress = 0
                    self.tasks[task.id] = task
                    loaded_count += 1
                elif task.status in ("completed", "failed"):
                    self.tasks[task.id] = task
            except Exception as e:
                logger.warning(f"加载任务文件失败 {json_file.name}: {e}")

        if loaded_count > 0:
            logger.info(f"已加载 {loaded_count} 个未完成任务")


# 全局单例
_task_manager: TaskManager | None = None
_task_manager_lock = threading.Lock()


def get_task_manager() -> TaskManager:
    """获取全局TaskManager单例

    Returns:
        TaskManager实例
    """
    global _task_manager
    if _task_manager is None:
        with _task_manager_lock:
            if _task_manager is None:
                _task_manager = TaskManager(max_workers=2)
                _task_manager.start()
    return _task_manager
