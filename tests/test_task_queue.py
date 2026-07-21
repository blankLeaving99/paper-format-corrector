"""Task queue and manager tests.

覆盖场景：
- 任务提交
- 状态查询
- 任务完成
- 任务失败
- 持久化恢复
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

import pytest

from paper_format_corrector.interfaces.api.task_manager import TaskInfo, TaskManager


class TestTaskManager:
    """TaskManager单元测试"""

    def setup_method(self):
        """每个测试前创建新的TaskManager"""
        self.tmp_dir = tempfile.mkdtemp()
        self.manager = TaskManager(max_workers=2, storage_dir=self.tmp_dir)
        self.manager.start()

    def teardown_method(self):
        """每个测试后清理"""
        self.manager.stop()

    def test_submit_task(self):
        """测试任务提交"""
        import threading

        # 使用一个慢速任务来确保我们能捕获到pending状态
        event = threading.Event()

        def slow_task():
            event.wait(timeout=5)
            return {"success": True}

        task_id = self.manager.submit(slow_task, task_type="test", filename="test.txt")

        assert task_id is not None
        assert len(task_id) > 0

        # 等待一小段时间让任务开始
        time.sleep(0.1)

        task = self.manager.get_task(task_id)
        assert task is not None
        # 任务可能是pending或processing，取决于线程调度
        assert task.status in ("pending", "processing")
        assert task.task_type == "test"

        # 释放任务
        event.set()
        time.sleep(0.2)

    def test_task_execution(self):
        """测试任务执行"""

        def success_task():
            return {"success": True, "output_path": "/tmp/output.docx"}

        task_id = self.manager.submit(success_task, task_type="correct")

        # 等待任务完成
        time.sleep(0.5)

        task = self.manager.get_task(task_id)
        assert task.status == "completed"
        assert task.progress == 100
        assert task.result_path == "/tmp/output.docx"

    def test_task_failure(self):
        """测试任务失败"""

        def failing_task():
            raise ValueError("处理失败")

        task_id = self.manager.submit(failing_task, task_type="correct")

        # 等待任务完成
        time.sleep(0.5)

        task = self.manager.get_task(task_id)
        assert task.status == "failed"
        assert "处理失败" in task.error

    def test_task_progress(self):
        """测试进度更新"""
        manager = TaskManager(max_workers=1, storage_dir=self.tmp_dir)

        def slow_task(update_progress):
            for i in range(0, 100, 10):
                update_progress(i)
                time.sleep(0.01)
            return {"success": True}

        # 手动创建任务并测试进度更新
        task_id = str(__import__("uuid").uuid4())
        task = TaskInfo(
            id=task_id,
            status="pending",
            progress=0,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
            updated_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
            file_path="",
            filename="test.txt",
            task_type="test",
        )
        manager.tasks[task_id] = task

        # 模拟进度更新
        manager.update_progress(task_id, 50)
        assert manager.tasks[task_id].progress == 50

        manager.update_progress(task_id, 100)
        assert manager.tasks[task_id].progress == 100

    def test_get_status(self):
        """测试状态查询"""

        def dummy_task():
            return {"success": True}

        task_id = self.manager.submit(dummy_task, task_type="test")

        status = self.manager.get_status(task_id)
        assert "id" in status
        assert "status" in status
        assert "progress" in status

    def test_get_status_not_found(self):
        """测试查询不存在的任务"""
        status = self.manager.get_status("nonexistent-id")
        assert "error" in status

    def test_persistence(self):
        """测试持久化"""
        import uuid

        # 创建一个任务并等待完成
        def dummy_task():
            return {"success": True}

        task_id = self.manager.submit(dummy_task, task_type="test")
        time.sleep(0.5)  # 等待任务完成

        # 停止当前manager
        self.manager.stop()

        # 验证JSON文件已创建
        json_files = list(Path(self.tmp_dir).glob("*.json"))
        assert len(json_files) > 0, f"应该有持久化文件，实际找到: {json_files}"

        # 创建新manager，应该加载已完成的任务
        new_manager = TaskManager(max_workers=1, storage_dir=self.tmp_dir)
        assert task_id in new_manager.tasks


class TestTaskInfo:
    """TaskInfo数据模型测试"""

    def test_to_dict(self):
        """测试序列化"""
        task = TaskInfo(
            id="test-id",
            status="pending",
            progress=0,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            file_path="/tmp/test.docx",
            filename="test.docx",
            task_type="correct",
        )

        d = task.to_dict()
        assert d["id"] == "test-id"
        assert d["status"] == "pending"
        assert d["task_type"] == "correct"


class TestAPIEndpoints:
    """API端点集成测试"""

    def setup_method(self):
        """设置测试客户端"""
        from fastapi.testclient import TestClient

        from paper_format_corrector.interfaces.api.app import app

        self.client = TestClient(app)

    def test_submit_correction_rejects_non_docx(self):
        """测试拒绝非docx文件"""
        response = self.client.post(
            "/api/v1/correct",
            files={"file": ("test.txt", b"content", "text/plain")},
        )
        assert response.status_code == 400

    def test_task_status_not_found(self):
        """测试查询不存在的任务"""
        response = self.client.get("/api/v1/tasks/nonexistent-id")
        assert response.status_code == 404

    def test_correct_status_not_found(self):
        """测试correct状态查询不存在的任务"""
        response = self.client.get("/api/v1/correct/status/nonexistent-id")
        assert response.status_code == 404

    def test_download_not_found(self):
        """测试下载不存在的任务"""
        response = self.client.get("/api/v1/correct/download/nonexistent-id")
        assert response.status_code == 404

    def test_batch_requires_files(self):
        """测试批量接口需要文件"""
        response = self.client.post("/api/v1/batch")
        assert response.status_code == 422  # Unprocessable Entity
