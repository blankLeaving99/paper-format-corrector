"""自动拉取服务

后台守护线程定期检查远程模板更新并自动下载。
线程为 daemon 模式，随主进程退出而退出。
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

from ..template_repository import TemplateRepository
from .version_checker import VersionChecker

logger = logging.getLogger(__name__)

# 默认检查间隔：24 小时
_DEFAULT_CHECK_INTERVAL = 86400


class AutoUpdater:
    """自动更新服务：后台线程定期检查并应用远程模板更新。"""

    def __init__(
        self,
        repo: TemplateRepository,
        checker: VersionChecker,
        check_interval: int = _DEFAULT_CHECK_INTERVAL,
    ):
        self.repo = repo
        self.checker = checker
        self.check_interval = check_interval
        self.running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def start_background_thread(self) -> None:
        """启动后台检查线程（daemon 模式）。"""
        with self._lock:
            if self.running:
                logger.info("自动更新线程已在运行")
                return
            self.running = True
            self._thread = threading.Thread(target=self._loop, daemon=True, name="template-updater")
            self._thread.start()
            logger.info("自动更新线程已启动，检查间隔: %ds", self.check_interval)

    def stop(self) -> None:
        """停止后台线程。"""
        with self._lock:
            self.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
            logger.info("自动更新线程已停止")

    def _loop(self) -> None:
        """后台循环：定期检查更新并应用。"""
        while self.running:
            try:
                self._check_and_apply()
            except Exception as e:
                logger.error("自动更新检查失败: %s", e)
            time.sleep(self.check_interval)

    def check_now(self) -> list[dict[str, Any]]:
        """立即执行一次检查并应用更新（供手动触发调用）。"""
        return self._check_and_apply()

    def _check_and_apply(self) -> list[dict[str, Any]]:
        """检查更新并应用，返回已更新的模板列表。"""
        updates = self.checker.check_updates()
        if not updates:
            logger.info("所有模板已是最新")
            return []

        logger.info("发现 %d 个模板更新", len(updates))
        applied: list[dict[str, Any]] = []
        for update in updates:
            try:
                self._apply_update(update)
                applied.append(update)
            except Exception as e:
                logger.error("应用更新失败 [%s]: %s", update.get("id", ""), e)
        return applied

    def _apply_update(self, update: dict[str, Any]) -> None:
        """应用单个模板更新。"""
        template_id = update["id"]
        action = update["action"]

        if action == "new":
            self._download_and_save(template_id, update.get("version", "1.0"))
            logger.info("新模板已下载: %s v%s", update.get("name", template_id), update.get("version", ""))
        elif action == "update":
            self._download_and_save(template_id, update.get("to_version", "1.0"))
            logger.info("模板已更新: %s v%s -> v%s", update.get("name", template_id),
                         update.get("from_version", ""), update.get("to_version", ""))
        else:
            logger.warning("未知更新操作: %s (template=%s)", action, template_id)

    def _download_and_save(self, template_id: str, version: str) -> None:
        """从远程下载模板并保存到本地数据库。"""
        config = self.checker.fetch_template_config(template_id)
        if config is None:
            raise RuntimeError(f"无法下载模板配置: {template_id}")

        # 提取模板元信息
        name = config.pop("name", template_id)
        description = config.pop("description", "")
        category = config.pop("category", "云端模板")
        source_url = self.checker.remote_url + f"{template_id}.yaml"

        # 保存到本地 manifest 缓存
        self._update_local_manifest(template_id, name, version, source_url)

        # 通过 TemplateRepository 保存（复用已有数据库操作）
        self.repo.save_remote_template(
            template_id=template_id,
            name=name,
            category=category,
            config=config,
            description=description,
            version=version,
            source_url=source_url,
        )

    def _update_local_manifest(
        self, template_id: str, name: str, version: str, source_url: str
    ) -> None:
        """更新本地 manifest 缓存。"""
        local_dir = Path("templates_cache")
        local_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = local_dir / "manifest.json"

        manifest: dict[str, Any] = {}
        if manifest_path.exists():
            try:
                with open(manifest_path, encoding="utf-8") as f:
                    manifest = json.load(f)
            except Exception:
                manifest = {}

        manifest[template_id] = {
            "name": name,
            "version": version,
            "source_url": source_url,
        }

        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("更新本地 manifest 失败: %s", e)
