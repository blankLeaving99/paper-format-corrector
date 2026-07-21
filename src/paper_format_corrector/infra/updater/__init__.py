"""云端模板更新模块

提供远程模板仓库的版本比对、自动拉取和手动更新功能。
"""

from __future__ import annotations

from .auto_updater import AutoUpdater
from .version_checker import VersionChecker

__all__ = ["AutoUpdater", "VersionChecker"]
