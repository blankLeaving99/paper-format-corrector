"""云端模板同步服务

从远程模板仓库检查版本差异并拉取更新。
同步过程记录到日志，不阻塞主流程。

设计要点:
- 使用 TemplateRecord.source_url 字段存储远程模板源地址
- 版本比对基于语义化版本号 (X.Y)
- 同步失败不影响本地正常使用
- 线程安全，可后台运行
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from .storage.template_repository import TemplateRepository

logger = logging.getLogger(__name__)

# 允许访问的远程主机白名单（防止 SSRF）
_ALLOWED_HOSTS: set[str] = {
    "raw.githubusercontent.com",
    "github.com",
    "localhost",
    "127.0.0.1",
}

_URL_SCHEMES = {"https", "http"}


def _validate_url(url: str) -> bool:
    """校验远程 URL 安全性（域名白名单 + HTTPS）"""
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in _URL_SCHEMES:
        return False
    if not parsed.hostname:
        return False
    if parsed.hostname not in ("localhost", "127.0.0.1") and parsed.scheme != "https":
        return False
    if parsed.hostname not in _ALLOWED_HOSTS:
        logger.warning("URL 域名不在白名单中: %s", parsed.hostname)
        return False
    return True


def _parse_version(version_str: str) -> tuple[int, ...]:
    """将语义化版本号字符串解析为可比较的元组。

    >>> _parse_version("2.1")
    (2, 1)
    >>> _parse_version("invalid")
    (0,)
    """
    parts = version_str.strip().split(".")
    result: list[int] = []
    for p in parts:
        try:
            result.append(int(p))
        except ValueError:
            break
    return tuple(result) if result else (0,)


def _version_is_newer(remote: str, local: str) -> bool:
    """判断远程版本是否比本地更新。"""
    return _parse_version(remote) > _parse_version(local)


class TemplateSyncService:
    """云端模板同步服务。

    从远程 manifest.json 获取模板列表，与本地数据库比对版本差异，
    并拉取有变更的模板。所有操作失败均降级为日志警告，不抛异常。
    """

    def __init__(
        self,
        repo: TemplateRepository,
        remote_url: str = "",
        interval_hours: int = 24,
    ):
        self.repo = repo
        self.remote_url = remote_url.rstrip("/") + "/" if remote_url else ""
        self.interval_hours = interval_hours
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def check_updates(self) -> list[dict[str, Any]]:
        """检查远程仓库中需要同步的模板。

        Returns:
            需要更新的模板列表，每项包含:
            - id: 远程模板 ID
            - action: "new" | "update"
            - version: 远程版本
            - name: 模板名称
            - from_version: (仅 update) 本地版本
        """
        if not self.remote_url:
            logger.debug("未配置远程仓库地址，跳过更新检查")
            return []

        remote_manifest = self._fetch_manifest()
        if remote_manifest is None:
            return []

        local_versions = self._get_local_versions()
        updates: list[dict[str, Any]] = []

        for template_id, remote_info in remote_manifest.items():
            remote_version = remote_info.get("version", "1.0")
            local_version = local_versions.get(template_id, "")

            if not local_version:
                updates.append({
                    "id": template_id,
                    "action": "new",
                    "version": remote_version,
                    "name": remote_info.get("name", template_id),
                })
            elif _version_is_newer(remote_version, local_version):
                updates.append({
                    "id": template_id,
                    "action": "update",
                    "from_version": local_version,
                    "to_version": remote_version,
                    "name": remote_info.get("name", template_id),
                })

        if updates:
            logger.info("检查到 %d 个模板需要同步", len(updates))
        else:
            logger.info("所有模板已是最新")

        return updates

    def pull_updates(self, updates: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        """拉取有变更的模板并入库。

        Args:
            updates: 需要更新的列表。若为 None 则先调用 check_updates()。

        Returns:
            已成功同步的模板列表。
        """
        if updates is None:
            updates = self.check_updates()

        if not updates:
            return []

        applied: list[dict[str, Any]] = []
        for update in updates:
            try:
                self._apply_update(update)
                applied.append(update)
                action_label = "新增" if update["action"] == "new" else "更新"
                logger.info("%s模板: %s v%s", action_label, update["name"], update.get("version", ""))
            except Exception as e:
                logger.warning("同步模板失败 [%s]: %s", update.get("id", ""), e)

        if applied:
            logger.info("成功同步 %d 个模板", len(applied))
        return applied

    def auto_sync(self, interval_hours: int | None = None) -> None:
        """启动后台定时同步守护线程。

        Args:
            interval_hours: 同步间隔（小时），None 使用构造参数值。
        """
        hours = interval_hours if interval_hours is not None else self.interval_hours
        with self._lock:
            if self._running:
                logger.info("自动同步线程已在运行")
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._sync_loop,
                args=(hours,),
                daemon=True,
                name="template-sync",
            )
            self._thread.start()
            logger.info("自动同步已启动，间隔 %d 小时", hours)

    def stop_sync(self) -> None:
        """停止后台同步线程。"""
        with self._lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
            logger.info("自动同步已停止")

    def sync_once(self) -> list[dict[str, Any]]:
        """立即执行一次同步（检查 + 拉取），供外部直接调用。"""
        try:
            return self.pull_updates()
        except Exception as e:
            logger.warning("同步失败: %s", e)
            return []

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _sync_loop(self, hours: float) -> None:
        """后台同步循环。"""
        interval_seconds = hours * 3600
        while self._running:
            try:
                self.sync_once()
            except Exception as e:
                logger.error("自动同步异常: %s", e)
            time.sleep(interval_seconds)

    def _fetch_manifest(self) -> dict[str, Any] | None:
        """获取远程 manifest.json，网络异常时返回 None（降级）。"""
        manifest_url = self.remote_url + "manifest.json"
        if not _validate_url(manifest_url):
            logger.warning("远程 URL 不安全或不在白名单中: %s", manifest_url)
            return None
        try:
            import requests
            response = requests.get(manifest_url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning("获取远程 manifest 失败: %s", e)
            return None

    def _get_local_versions(self) -> dict[str, str]:
        """获取本地所有模板的版本映射 {template_id: version}。"""
        versions: dict[str, str] = {}
        try:
            templates = self.repo.list_templates(active_only=False)
            for t in templates:
                template_id = t.slug
                for prefix in ("remote-", "personal-", "builtin-"):
                    if template_id.startswith(prefix):
                        template_id = template_id[len(prefix):]
                        break
                versions[template_id] = t.version
        except Exception as e:
            logger.debug("获取本地模板版本失败: %s", e)
        return versions

    def _apply_update(self, update: dict[str, Any]) -> None:
        """应用单个模板更新（下载配置并保存到数据库）。"""
        template_id = update["id"]
        config = self._fetch_template_config(template_id)
        if config is None:
            raise RuntimeError(f"无法下载模板配置: {template_id}")

        name = config.pop("name", template_id)
        description = config.pop("description", "")
        category = config.pop("category", "云端模板")
        version = update.get("to_version", update.get("version", "1.0"))
        source_url = self.remote_url + f"{template_id}.yaml"

        self.repo.save_remote_template(
            template_id=template_id,
            name=name,
            category=category,
            config=config,
            description=description,
            version=version,
            source_url=source_url,
        )

    def _fetch_template_config(self, template_id: str) -> dict[str, Any] | None:
        """从远程获取单个模板配置。"""
        url = self.remote_url + f"{template_id}.yaml"
        if not _validate_url(url):
            logger.warning("模板 URL 不安全: %s", url)
            return None
        try:
            import requests
            import yaml
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return yaml.safe_load(response.text) or {}
        except Exception as e:
            logger.warning("下载模板配置失败 [%s]: %s", template_id, e)
            return None
