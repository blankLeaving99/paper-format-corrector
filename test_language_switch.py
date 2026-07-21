"""Quick test for language font switching feature."""
from __future__ import annotations
import sys
sys.path.insert(0, "src")

from paper_format_corrector.application.style_workbench import (
    get_language_font_config,
    manual_style_config,
    LANGUAGE_FONT_PRESETS,
)


def test_presets():
    print("=== 1. LANGUAGE_FONT_PRESETS ===")
    for k, v in LANGUAGE_FONT_PRESETS.items():
        label = v["label"]
        body = v["body_font"]
        heading = v["heading_font"]
        en = v["en_font"]
        print(f"  {k}: {label} — 正文:{body} 标题:{heading} 英文:{en}")
    assert len(LANGUAGE_FONT_PRESETS) == 5, f"Expected 5 presets, got {len(LANGUAGE_FONT_PRESETS)}"
    print("  PASS\n")


def test_get_language_font_config():
    print("=== 2. get_language_font_config() ===")
    for lang in ["auto", "chinese", "english", "japanese", "korean"]:
        cfg = get_language_font_config(lang)
        print(f"  {lang}: {cfg}")
        assert "body_font" in cfg
        assert "heading_font" in cfg
        assert "en_font" in cfg
    # Verify specific fonts
    ja = get_language_font_config("japanese")
    assert ja["body_font"] == "MS Mincho", f"Expected MS Mincho, got {ja['body_font']}"
    assert ja["heading_font"] == "MS Gothic", f"Expected MS Gothic, got {ja['heading_font']}"
    ko = get_language_font_config("korean")
    assert ko["body_font"] == "Batang", f"Expected Batang, got {ko['body_font']}"
    print("  PASS\n")


def test_manual_style_config_auto():
    print("=== 3. manual_style_config() with auto ===")
    result = manual_style_config(
        body_font="宋体", body_size=12, body_line_spacing=1.5, body_indent=2,
        heading1_size=16, heading2_size=14, heading3_size=12, heading_font="黑体",
        table_style="three_line", table_font_size=10.5, image_max_width="full",
        language="auto",
    )
    font = result["format_rules"]["font"]
    print(f"  chinese={font.get('chinese')}, english={font.get('english')}, heading={font.get('heading_chinese')}")
    assert font["chinese"] == "宋体"
    assert font["english"] == "Times New Roman"
    assert font["heading_chinese"] == "黑体"
    print("  PASS\n")


def test_manual_style_config_japanese():
    print("=== 4. manual_style_config() with japanese ===")
    result = manual_style_config(
        body_font="", body_size=12, body_line_spacing=1.5, body_indent=2,
        heading1_size=16, heading2_size=14, heading3_size=12, heading_font="",
        table_style="three_line", table_font_size=10.5, image_max_width="full",
        language="japanese",
    )
    font = result["format_rules"]["font"]
    print(f"  chinese={font.get('chinese')}, english={font.get('english')}, heading={font.get('heading_chinese')}")
    print(f"  japanese={font.get('japanese')}, japanese_heading={font.get('japanese_heading')}")
    assert font["chinese"] == "MS Mincho", f"Expected MS Mincho, got {font['chinese']}"
    assert font["heading_chinese"] == "MS Gothic", f"Expected MS Gothic, got {font['heading_chinese']}"
    assert font.get("japanese") == "MS Mincho"
    assert font.get("japanese_heading") == "MS Gothic"
    print("  PASS\n")


def test_manual_style_config_korean():
    print("=== 5. manual_style_config() with korean ===")
    result = manual_style_config(
        body_font="", body_size=12, body_line_spacing=1.5, body_indent=2,
        heading1_size=16, heading2_size=14, heading3_size=12, heading_font="",
        table_style="three_line", table_font_size=10.5, image_max_width="full",
        language="korean",
    )
    font = result["format_rules"]["font"]
    print(f"  chinese={font.get('chinese')}, english={font.get('english')}, heading={font.get('heading_chinese')}")
    print(f"  korean={font.get('korean')}, korean_heading={font.get('korean_heading')}")
    assert font["chinese"] == "Batang", f"Expected Batang, got {font['chinese']}"
    assert font["heading_chinese"] == "Gothic", f"Expected Gothic, got {font['heading_chinese']}"
    assert font.get("korean") == "Batang"
    assert font.get("korean_heading") == "Gothic"
    print("  PASS\n")


def test_manual_override_with_language():
    print("=== 6. User override + language ===")
    result = manual_style_config(
        body_font="楷体", body_size=14, body_line_spacing=2.0, body_indent=2,
        heading1_size=18, heading2_size=16, heading3_size=14, heading_font="微软雅黑",
        table_style="full_border", table_font_size=11, image_max_width="80%",
        language="japanese",
    )
    font = result["format_rules"]["font"]
    print(f"  User override (楷体/微软雅黑) + language=japanese")
    print(f"  Result: chinese={font['chinese']}, heading={font['heading_chinese']}")
    # User override should take precedence
    assert font["chinese"] == "楷体", f"Expected 楷体, got {font['chinese']}"
    assert font["heading_chinese"] == "微软雅黑", f"Expected 微软雅黑, got {font['heading_chinese']}"
    print("  PASS\n")


def test_format_rules_structure():
    print("=== 7. Full format_rules structure ===")
    result = manual_style_config(
        body_font="宋体", body_size=12, body_line_spacing=1.5, body_indent=2,
        heading1_size=16, heading2_size=14, heading3_size=12, heading_font="黑体",
        table_style="three_line", table_font_size=10.5, image_max_width="full",
        language="chinese",
    )
    fr = result["format_rules"]
    assert "font" in fr
    assert "body_text" in fr
    assert "headings" in fr
    assert "tables" in fr
    assert "images" in fr
    assert fr["body_text"]["font_size"] == 12
    assert fr["headings"]["heading1"]["font_size"] == 16
    print(f"  All keys present: {list(fr.keys())}")
    print("  PASS\n")


if __name__ == "__main__":
    test_presets()
    test_get_language_font_config()
    test_manual_style_config_auto()
    test_manual_style_config_japanese()
    test_manual_style_config_korean()
    test_manual_override_with_language()
    test_format_rules_structure()
    print("=" * 50)
    print("ALL 7 TESTS PASSED")
