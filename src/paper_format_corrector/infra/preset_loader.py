"""Format preset loader.

Loads predefined format configurations for different journal/thesis standards.
Presets are YAML files in the presets/ directory.
"""

from __future__ import annotations

import os
import re
import yaml
from pathlib import Path


def _presets_dir() -> Path:
    """Return the presets directory path."""
    # Walk up from this file to find the project root
    here = Path(__file__).resolve()
    for parent in here.parents:
        presets = parent / "presets"
        if presets.is_dir():
            return presets
    # Fallback: relative to cwd
    return Path("presets")


def list_presets() -> list[dict[str, str]]:
    """Return a list of available presets with their metadata.

    Each dict contains: name, description, path
    """
    presets_dir = _presets_dir()
    result = []

    if not presets_dir.is_dir():
        return result

    for yaml_file in sorted(presets_dir.glob("*.yaml")):
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            result.append({
                "name": yaml_file.stem,
                "description": data.get("description", yaml_file.stem),
                "path": str(yaml_file),
            })
        except Exception:
            result.append({
                "name": yaml_file.stem,
                "description": yaml_file.stem,
                "path": str(yaml_file),
            })

    return result


def get_preset_choices() -> list[str]:
    """Return a list of preset names for use in CLI/GUI choices."""
    return [p["name"] for p in list_presets()]


def load_preset(name: str) -> dict:
    """Load a preset config by name.

    Args:
        name: Preset name (e.g., 'ieee', 'nature', 'chinese_thesis')

    Returns:
        The preset configuration dict (format_rules + auto_detect)

    Raises:
        FileNotFoundError: If the preset file doesn't exist
    """
    presets_dir = _presets_dir()

    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        raise ValueError(f"Invalid preset name: {name}")

    preset_path = (presets_dir / name).resolve()
    if not str(preset_path).startswith(str(presets_dir.resolve()) + os.sep):
        raise ValueError(f"Preset path traversal detected: {name}")

    preset_path = preset_path.with_suffix('.yaml')

    if not preset_path.exists():
        available = ", ".join(get_preset_choices())
        raise FileNotFoundError(
            f"Preset '{name}' not found at {preset_path}. "
            f"Available presets: {available}"
        )

    with open(preset_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Remove the description field (metadata only, not config)
    data.pop("description", None)
    return data


def format_preset_list() -> str:
    """Format the preset list for display in terminal/GUI."""
    presets = list_presets()
    if not presets:
        return "No presets found."

    lines = ["Available format presets:", ""]
    for p in presets:
        lines.append(f"  {p['name']:<20s} {p['description']}")
    return "\n".join(lines)
