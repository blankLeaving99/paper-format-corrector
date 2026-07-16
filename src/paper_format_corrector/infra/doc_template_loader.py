"""文档模板加载器 v2

加载 presets/doc_templates/ 目录下的文档模板预设，
以及用户自定义模板（~/.paper-format-corrector/templates/）。
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml


def _doc_templates_dir() -> Path:
    """返回内置文档模板目录路径"""
    here = Path(__file__).resolve()
    for parent in here.parents:
        templates = parent / "presets" / "doc_templates"
        if templates.is_dir():
            return templates
    return Path("presets/doc_templates")


def _user_templates_dir() -> Path:
    """返回用户自定义模板目录路径"""
    return Path.home() / ".paper-format-corrector" / "templates"


def list_doc_templates() -> list[dict[str, str]]:
    """列出所有可用的文档模板（内置+用户自定义）"""
    result = []

    # 内置模板
    templates_dir = _doc_templates_dir()
    if templates_dir.is_dir():
        for yaml_file in sorted(templates_dir.glob("*.yaml")):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                result.append({
                    "name": yaml_file.stem,
                    "description": data.get("description", yaml_file.stem),
                    "path": str(yaml_file),
                    "source": "builtin",
                    "doc_type_hints": data.get("doc_type_hints", []),
                    "format_rules": data.get("format_rules", {}),
                })
            except Exception:
                result.append({
                    "name": yaml_file.stem,
                    "description": yaml_file.stem,
                    "path": str(yaml_file),
                    "source": "builtin",
                    "doc_type_hints": [],
                    "format_rules": {},
                })

    # 用户自定义模板
    user_dir = _user_templates_dir()
    if user_dir.is_dir():
        for yaml_file in sorted(user_dir.glob("*.yaml")):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                result.append({
                    "name": f"user_{yaml_file.stem}",
                    "description": data.get("description", yaml_file.stem),
                    "path": str(yaml_file),
                    "source": "user",
                    "doc_type_hints": data.get("doc_type_hints", []),
                    "format_rules": data.get("format_rules", {}),
                })
            except Exception:
                pass

    return result


def get_doc_template_choices() -> list[str]:
    """返回文档模板名称列表，用于CLI/GUI选择"""
    return [t["name"] for t in list_doc_templates()]


def load_doc_template(name: str) -> dict:
    """加载指定的文档模板

    Args:
        name: 模板名称（如 'report', 'official_doc', 'contract'）
              用户模板以 'user_' 前缀标识

    Returns:
        模板配置字典（format_rules + doc_type_hints）

    Raises:
        FileNotFoundError: 模板文件不存在
    """
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        raise ValueError(f"Invalid template name: {name}")

    # 用户模板
    if name.startswith("user_"):
        user_dir = _user_templates_dir()
        template_name = name[5:]  # 去掉 user_ 前缀
        template_path = (user_dir / template_name).resolve()
        if not str(template_path).startswith(str(user_dir.resolve()) + os.sep):
            raise ValueError(f"Template path traversal detected: {name}")
        template_path = template_path.with_suffix('.yaml')
    else:
        # 内置模板
        templates_dir = _doc_templates_dir()
        template_path = (templates_dir / name).resolve()
        if not str(template_path).startswith(str(templates_dir.resolve()) + os.sep):
            raise ValueError(f"Template path traversal detected: {name}")
        template_path = template_path.with_suffix('.yaml')

    if not template_path.exists():
        available = ", ".join(get_doc_template_choices())
        raise FileNotFoundError(
            f"Template '{name}' not found. Available: {available}"
        )

    with open(template_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data


def save_user_template(name: str, config: dict) -> str:
    """保存用户自定义模板

    Args:
        name: 模板名称（仅字母数字下划线连字符）
        config: 模板配置字典

    Returns:
        保存的文件路径

    Raises:
        ValueError: 模板名称无效或配置结构不合法
    """
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        raise ValueError(f"Invalid template name: {name}. Use only letters, numbers, underscore, hyphen.")

    if not isinstance(config, dict):
        raise ValueError("config 必须是字典类型")

    # 验证必要结构
    if "format_rules" in config and not isinstance(config["format_rules"], dict):
        raise ValueError("format_rules 必须是字典类型")

    user_dir = _user_templates_dir()
    user_dir.mkdir(parents=True, exist_ok=True)

    template_path = user_dir / f"{name}.yaml"

    # 确保不覆盖内置模板
    builtin_dir = _doc_templates_dir()
    builtin_path = (builtin_dir / name).with_suffix('.yaml')
    if builtin_path.exists():
        raise ValueError(f"Cannot overwrite builtin template '{name}'. Use a different name.")

    with open(template_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

    return str(template_path)


def delete_user_template(name: str) -> bool:
    """删除用户自定义模板

    Args:
        name: 模板名称（不含 user_ 前缀）

    Returns:
        是否成功删除
    """
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        return False

    user_dir = _user_templates_dir()
    template_path = (user_dir / name).with_suffix('.yaml')

    if not template_path.exists():
        return False

    template_path.unlink()
    return True


def list_user_templates() -> list[dict[str, str]]:
    """列出用户自定义模板"""
    result = []
    user_dir = _user_templates_dir()

    if not user_dir.is_dir():
        return result

    for yaml_file in sorted(user_dir.glob("*.yaml")):
        try:
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            result.append({
                "name": yaml_file.stem,
                "description": data.get("description", yaml_file.stem),
                "path": str(yaml_file),
                "doc_type_hints": data.get("doc_type_hints", []),
                "format_rules": data.get("format_rules", {}),
            })
        except Exception:
            pass

    return result


def get_template_for_doc_type(doc_type: str) -> dict | None:
    """根据文档类型自动选择最匹配的模板

    Args:
        doc_type: 用户描述的文档类型（如"合同"、"报告"等）

    Returns:
        最匹配的模板配置，如果没有匹配则返回None
    """
    templates = list_doc_templates()
    doc_type_lower = doc_type.lower()

    best_match = None
    best_score = 0

    for template in templates:
        hints = template.get("doc_type_hints", [])
        for hint in hints:
            if hint in doc_type_lower or doc_type_lower in hint:
                # 精确匹配得分更高
                score = len(hint) / max(len(doc_type_lower), 1)
                if score > best_score:
                    best_score = score
                    best_match = template

    return best_match
