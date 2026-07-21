"""外部工具查找与管理

提供 LibreOffice 等外部工具的路径查找、缓存功能。
"""

from __future__ import annotations

import shutil
from functools import lru_cache
from pathlib import Path

# ── LibreOffice 查找 ────────────────────────────────────────────────

_LIBREOFFICE_CANDIDATES = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    r"D:\Program Files\LibreOffice\program\soffice.exe",
    r"D:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/usr/bin/libreoffice",
    "/usr/bin/soffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]


@lru_cache(maxsize=1)
def find_libreoffice() -> str | None:
    """查找 LibreOffice 安装路径

    优先检查绝对路径（避免 PATH 污染风险），最后回退到 PATH 搜索。
    结果会被缓存，多次调用无额外开销。

    Returns:
        LibreOffice 可执行文件路径，未找到返回 None
    """
    # 检查已知安装路径
    for candidate in _LIBREOFFICE_CANDIDATES:
        if Path(candidate).exists():
            return candidate

    # PATH 搜索仅作最后回退
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found

    return None
