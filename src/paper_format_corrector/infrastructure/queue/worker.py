"""后台Worker

多线程Worker从队列中获取任务并执行文档矫正。
"""

from __future__ import annotations

import logging
import tempfile
import threading
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .task_queue import TaskQueue

logger = logging.getLogger(__name__)


class Worker:
    """后台任务处理Worker

    启动多个守护线程从队列中获取任务并执行矫正操作。
    支持进度回调和任务状态持久化。
    """

    def __init__(self, queue: TaskQueue, num_workers: int = 2) -> None:
        """初始化Worker

        Args:
            queue: 任务队列
            num_workers: Worker线程数量
        """
        self.queue = queue
        self.num_workers = num_workers
        self.workers: list[threading.Thread] = []
        self.running = False
        self._lock = threading.Lock()

    def start(self) -> None:
        """启动Worker线程"""
        with self._lock:
            if self.running:
                logger.warning("Worker已在运行中")
                return

            self.running = True
            for i in range(self.num_workers):
                t = threading.Thread(
                    target=self._process_loop,
                    name=f"worker-{i}",
                    daemon=True,
                )
                t.start()
                self.workers.append(t)

            logger.info(f"已启动 {self.num_workers} 个Worker线程")

    def stop(self) -> None:
        """停止Worker线程"""
        with self._lock:
            self.running = False

        # 等待所有Worker结束
        for t in self.workers:
            t.join(timeout=5)
        self.workers.clear()
        logger.info("所有Worker已停止")

    def _process_loop(self) -> None:
        """Worker主循环"""
        while self.running:
            try:
                task_id = self.queue.queue.get(timeout=1)
                self._process_task(task_id)
            except Exception:
                # Queue.get超时会抛出Empty异常，这是正常行为
                continue

    def _process_task(self, task_id: str) -> None:
        """处理单个任务

        Args:
            task_id: 任务ID
        """
        task = self.queue.get_task(task_id)
        if not task:
            logger.warning(f"任务不存在: {task_id}")
            return

        try:
            # 更新状态为处理中
            self.queue.update_task(task_id, status="processing", progress=10)
            logger.info(f"开始处理任务: {task_id}")

            # 执行矫正
            result = self._run_correction(task_id)

            # 更新为完成状态
            if result and result.get("success"):
                self.queue.update_task(
                    task_id,
                    status="completed",
                    progress=100,
                    result_path=result.get("output_path"),
                )
                logger.info(f"任务完成: {task_id}")
            else:
                error_msg = result.get("error", "未知错误") if result else "处理返回空结果"
                self.queue.update_task(task_id, status="failed", error=error_msg)
                logger.error(f"任务失败: {task_id}, 原因: {error_msg}")

        except Exception as e:
            self.queue.update_task(task_id, status="failed", error=str(e))
            logger.error(f"任务异常: {task_id}, 错误: {e}", exc_info=True)

    def _run_correction(self, task_id: str) -> dict:
        """执行文档矫正

        Args:
            task_id: 任务ID

        Returns:
            处理结果字典
        """
        from paper_format_corrector.app import PaperFormatCorrector

        task = self.queue.get_task(task_id)
        if not task:
            return {"success": False, "error": "任务不存在"}

        try:
            # 更新进度
            self.queue.update_task(task_id, progress=20)

            # 初始化矫正器
            corrector = PaperFormatCorrector()
            if task.template_id:
                corrector.apply_preset(task.template_id)

            self.queue.update_task(task_id, progress=40)

            # 执行矫正
            output_dir = Path(tempfile.mkdtemp())
            output_path = output_dir / f"corrected_{task.filename}"

            report = corrector.corrector.correct_document(task.file_path, str(output_path))

            self.queue.update_task(task_id, progress=90)

            # 验证输出
            if not output_path.exists():
                return {"success": False, "error": "矫正失败：未生成输出文件"}

            return {
                "success": True,
                "output_path": str(output_path),
                "report": report,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
