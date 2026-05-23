"""路径安全校验工具

防止路径穿越攻击和非法路径访问。
"""

import os
from pathlib import Path

# 允许的文件扩展名
ALLOWED_INPUT_EXTENSIONS = {
    ".docx", ".doc", ".odt", ".rtf", ".pdf", ".txt", ".md", ".markdown", ".tex",
    ".yaml", ".yml",
}

ALLOWED_OUTPUT_EXTENSIONS = {
    ".docx", ".doc", ".pdf", ".html", ".txt", ".md", ".markdown",
    ".diff.html",
}


def validate_input_path(path: str, allowed_extensions: set = None) -> Path:
    """校验输入文件路径安全性

    Args:
        path: 文件路径
        allowed_extensions: 允许的扩展名集合，None 表示不限制

    Returns:
        校验后的 Path 对象

    Raises:
        ValueError: 路径不安全或扩展名不允许
        FileNotFoundError: 文件不存在
    """
    p = Path(path).resolve()

    # 检查文件是否存在
    if not p.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    # 检查是否为文件（不是目录）
    if not p.is_file():
        raise ValueError(f"路径不是文件: {path}")

    # 检查扩展名
    if allowed_extensions and p.suffix.lower() not in allowed_extensions:
        raise ValueError(f"不允许的文件类型: {p.suffix}，允许: {allowed_extensions}")

    return p


def validate_output_path(path: str, allowed_extensions: set = None) -> Path:
    """校验输出文件路径安全性

    Args:
        path: 文件路径
        allowed_extensions: 允许的扩展名集合

    Returns:
        校验后的 Path 对象
    """
    p = Path(path).resolve()

    # 检查扩展名
    if allowed_extensions and p.suffix.lower() not in allowed_extensions:
        raise ValueError(f"不允许的输出文件类型: {p.suffix}")

    # 确保输出目录存在
    p.parent.mkdir(parents=True, exist_ok=True)

    return p


def safe_join(base_dir: str, filename: str) -> Path:
    """安全地拼接路径，防止路径穿越

    Args:
        base_dir: 基础目录
        filename: 文件名（不允许包含路径分隔符）

    Returns:
        安全的完整路径
    """
    base = Path(base_dir).resolve()

    # 文件名不允许包含路径分隔符
    if "/" in filename or "\\" in filename:
        raise ValueError(f"文件名不允许包含路径分隔符: {filename}")

    # 不允许 ..
    if ".." in filename:
        raise ValueError(f"文件名不允许包含 '..': {filename}")

    result = (base / filename).resolve()

    # 确保结果在 base 目录下（用 os.sep 确保前缀匹配准确）
    base_str = str(base)
    result_str = str(result)
    if not result_str.startswith(base_str + os.sep) and result_str != base_str:
        raise ValueError(f"路径穿越检测: {result} 不在 {base} 下")

    return result
