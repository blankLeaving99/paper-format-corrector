"""新增预设测试"""

import pytest
import yaml

from paper_format_corrector.infra.preset_loader import load_preset


class TestNewPresets:
    """新增预设加载测试"""

    def test_load_springer(self):
        """测试加载 Springer 预设"""
        preset = load_preset("springer")

        assert preset is not None
        assert "format_rules" in preset

        rules = preset["format_rules"]
        assert "font" in rules
        assert "headings" in rules
        assert "body_text" in rules
        assert "margins" in rules
        assert "references" in rules

    def test_load_elsevier(self):
        """测试加载 Elsevier 预设"""
        preset = load_preset("elsevier")

        assert preset is not None
        assert "format_rules" in preset

        rules = preset["format_rules"]
        assert "font" in rules
        assert "headings" in rules
        assert "body_text" in rules

    def test_load_acm(self):
        """测试加载 ACM 预设"""
        preset = load_preset("acm")

        assert preset is not None
        assert "format_rules" in preset

        rules = preset["format_rules"]
        assert "font" in rules
        assert "headings" in rules
        assert "body_text" in rules

    def test_preset_format_rules_structure(self):
        """测试预设格式规则结构"""
        for name in ["springer", "elsevier", "acm"]:
            preset = load_preset(name)
            rules = preset["format_rules"]

            # 检查必要的键
            assert "font" in rules, f"{name} 缺少 font"
            assert "headings" in rules, f"{name} 缺少 headings"
            assert "body_text" in rules, f"{name} 缺少 body_text"
            assert "margins" in rules, f"{name} 缺少 margins"

            # 检查标题层级
            headings = rules["headings"]
            assert "heading1" in headings, f"{name} 缺少 heading1"
            assert "heading2" in headings, f"{name} 缺少 heading2"
            assert "heading3" in headings, f"{name} 缺少 heading3"

    def test_preset_auto_detect(self):
        """测试预设自动检测规则"""
        for name in ["springer", "elsevier", "acm"]:
            preset = load_preset(name)

            assert "auto_detect" in preset, f"{name} 缺少 auto_detect"
            detect = preset["auto_detect"]
            assert "chapter_pattern" in detect, f"{name} 缺少 chapter_pattern"
            assert "section_pattern" in detect, f"{name} 缺少 section_pattern"

    def test_springer_body_font_size(self):
        """测试 Springer 正文字号"""
        preset = load_preset("springer")
        body_size = preset["format_rules"]["body_text"]["font_size"]
        assert body_size == 9  # Springer 使用 9pt

    def test_elsevier_body_font_size(self):
        """测试 Elsevier 正文字号"""
        preset = load_preset("elsevier")
        body_size = preset["format_rules"]["body_text"]["font_size"]
        assert body_size == 10  # Elsevier 使用 10pt

    def test_acm_body_font_size(self):
        """测试 ACM 正文字号"""
        preset = load_preset("acm")
        body_size = preset["format_rules"]["body_text"]["font_size"]
        assert body_size == 9  # ACM 使用 9pt


class TestPresetYAML:
    """预设 YAML 文件测试"""

    def test_springer_yaml_valid(self):
        """测试 Springer YAML 语法"""
        from pathlib import Path

        yaml_path = Path("presets/springer.yaml")
        if yaml_path.exists():
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            assert data is not None
            assert "format_rules" in data

    def test_elsevier_yaml_valid(self):
        """测试 Elsevier YAML 语法"""
        from pathlib import Path

        yaml_path = Path("presets/elsevier.yaml")
        if yaml_path.exists():
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            assert data is not None
            assert "format_rules" in data

    def test_acm_yaml_valid(self):
        """测试 ACM YAML 语法"""
        from pathlib import Path

        yaml_path = Path("presets/acm.yaml")
        if yaml_path.exists():
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            assert data is not None
            assert "format_rules" in data
