"""远程模板仓库版本比对服务

从远程 manifest.json 获取模板列表，与本地数据库比对版本差异。
提供离线降级能力，网络不可用时返回空列表而非报错。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# 允许访问的远程主机白名单（防止 SSRF）
_ALLOWED_HOSTS: set[str] = {
    "raw.githubusercontent.com",
    "github.com",
    "localhost",
    "127.0.0.1",
}

# URL 模式白名单
_URL_SCHEMES = {"https", "http"}


def _validate_url(url: str) -> bool:
    """校验远程 URL 安全性（域名白名单 + HTTPS）"""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in _URL_SCHEMES:
        return False
    if not parsed.hostname:
        return False
    # localhost/127.0.0.1 允许 HTTP，其他必须 HTTPS
    if parsed.hostname not in ("localhost", "127.0.0.1") and parsed.scheme != "https":
        return False
    if parsed.hostname not in _ALLOWED_HOSTS:
        logger.warning("URL 域名不在白名单中: %s", parsed.hostname)
        return False
    return True


class VersionChecker:
    """版本比对服务：获取远程 manifest 并与本地模板数据库比对。"""

    def __init__(self, remote_url: str):
        # 规范化 remote_url 以确保以 / 结尾
        self.remote_url = remote_url.rstrip("/") + "/"
        self.manifest_url = self.remote_url + "manifest.json"

    def check_updates(self, local_versions: dict[str, str] | None = None) -> list[dict[str, Any]]:
        """检查远程仓库中的模板更新。

        Args:
            local_versions: 本地模板 {template_id: version} 映射。
                若为 None 则从本地 manifest 文件加载。

        Returns:
            需要更新的模板列表，每项包含 id/action/version/name 等字段。
        """
        remote_manifest = self._fetch_manifest()
        if remote_manifest is None:
            logger.info("无法获取远程 manifest，跳过更新检查")
            return []

        if local_versions is None:
            local_manifest = self._load_local_manifest()
            local_versions = {k: v.get("version", "") for k, v in local_manifest.items()}

        updates: list[dict[str, Any]] = []
        for template_id, remote_info in remote_manifest.items():
            local_version = local_versions.get(template_id)
            if not local_version:
                updates.append({
                    "id": template_id,
                    "action": "new",
                    "version": remote_info.get("version", "1.0"),
                    "name": remote_info.get("name", template_id),
                })
            elif local_version != remote_info.get("version", ""):
                updates.append({
                    "id": template_id,
                    "action": "update",
                    "from_version": local_version,
                    "to_version": remote_info.get("version", ""),
                    "name": remote_info.get("name", template_id),
                })
        return updates

    def _fetch_manifest(self) -> dict[str, Any] | None:
        """获取远程 manifest.json，网络异常时返回 None（降级）。"""
        if not _validate_url(self.manifest_url):
            logger.warning("远程 URL 不安全或不在白名单中: %s", self.manifest_url)
            return None
        try:
            import requests
            response = requests.get(self.manifest_url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning("获取远程 manifest 失败: %s", e)
            return None

    def _load_local_manifest(self) -> dict[str, Any]:
        """从本地缓存目录加载 manifest。"""
        local_path = Path("templates_cache") / "manifest.json"
        if not local_path.exists():
            return {}
        try:
            with open(local_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.debug("加载本地 manifest 失败: %s", e)
            return {}

    def save_local_manifest(self, manifest: dict[str, Any]) -> None:
        """保存 manifest 到本地缓存。"""
        local_dir = Path("templates_cache")
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / "manifest.json"
        try:
            with open(local_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("保存本地 manifest 失败: %s", e)

    def fetch_template_config(self, template_id: str) -> dict[str, Any] | None:
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
