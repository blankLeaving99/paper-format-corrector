"""Tests for the requirement parser: natural language, table, and mixed formats."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from paper_format_corrector.parsers.requirement_parser import RequirementParser


def _parse_and_assert_basics(path):
    """Parse a requirement file and return the config for further assertions."""
    parser = RequirementParser()
    config = parser.parse(path)
    assert config is not None, f"Parser should return a config for {path}"
    assert isinstance(config, dict), "Parsed config should be a dict"
    return config


def test_parse_natural_language(requirement_natural_path):
    """Parse a natural language requirement and verify key fields."""
    config = _parse_and_assert_basics(requirement_natural_path)
    fr = config.get("format_rules", {})

    # Font
    font = fr.get("font", {})
    assert font.get("chinese") is not None, "Chinese font should be set"
    assert font.get("heading_chinese") is not None, "Heading font should be set"

    # Headings
    h1 = fr.get("headings", {}).get("heading1", {})
    assert h1.get("font_size") == 22, "Heading1 font_size should be 22 (二号)"
    assert h1.get("bold") is True, "Heading1 should be bold"
    assert h1.get("align") == "center", "Heading1 should be centered"

    h2 = fr.get("headings", {}).get("heading2", {})
    assert h2.get("font_size") == 16, "Heading2 font_size should be 16 (三号)"
    assert h2.get("align") == "left", "Heading2 should be left-aligned"

    h3 = fr.get("headings", {}).get("heading3", {})
    assert h3.get("font_size") == 14, "Heading3 font_size should be 14 (四号)"

    # Body text
    body = fr.get("body_text", {})
    assert body.get("font_size") == 12, "Body font_size should be 12 (小四)"
    ls = body.get("line_spacing")
    assert ls is not None, "Body line_spacing should be set"
    if isinstance(ls, dict):
        assert ls.get("value") == 1.5
    else:
        assert ls == 1.5

    assert body.get("first_line_indent") == 2.0, "Body first_line_indent should be 2"
    assert body.get("align") == "justify", "Body align should be justify"


def test_parse_table_format(requirement_table_path):
    """Parse a table-format requirement and verify key fields."""
    config = _parse_and_assert_basics(requirement_table_path)
    fr = config.get("format_rules", {})

    font = fr.get("font", {})
    assert font.get("chinese") is not None

    h1 = fr.get("headings", {}).get("heading1", {})
    assert h1.get("font_size") == 22
    assert h1.get("bold") is True

    body = fr.get("body_text", {})
    assert body.get("font_size") == 12

    ls = body.get("line_spacing")
    if isinstance(ls, dict):
        assert ls.get("value") == 1.5
    else:
        assert ls == 1.5


def test_parse_mixed_docx(requirement_mixed_path):
    """Parse a mixed-format .docx requirement and verify key fields."""
    config = _parse_and_assert_basics(requirement_mixed_path)
    fr = config.get("format_rules", {})

    body = fr.get("body_text", {})
    assert body.get("font_size") == 12, "Body font_size should be 12 (小四)"

    ls = body.get("line_spacing")
    if isinstance(ls, dict):
        assert ls.get("value") == 1.5
    else:
        assert ls == 1.5

    h1 = fr.get("headings", {}).get("heading1", {})
    assert h1.get("font_size") == 22


def test_three_formats_consistent(requirement_natural_path, requirement_table_path, requirement_mixed_path):
    """Verify that all three format parsers produce consistent key values."""
    c1 = _parse_and_assert_basics(requirement_natural_path)
    c2 = _parse_and_assert_basics(requirement_table_path)
    c3 = _parse_and_assert_basics(requirement_mixed_path)

    for label, c in [("natural", c1), ("table", c2), ("mixed", c3)]:
        body_size = c.get("format_rules", {}).get("body_text", {}).get("font_size")
        assert body_size == 12, f"[{label}] body font_size should be 12, got {body_size}"

        h1_size = c.get("format_rules", {}).get("headings", {}).get("heading1", {}).get("font_size")
        assert h1_size == 22, f"[{label}] heading1 font_size should be 22, got {h1_size}"

        h2_size = c.get("format_rules", {}).get("headings", {}).get("heading2", {}).get("font_size")
        assert h2_size == 16, f"[{label}] heading2 font_size should be 16, got {h2_size}"

        ls = c.get("format_rules", {}).get("body_text", {}).get("line_spacing")
        if isinstance(ls, dict):
            assert ls.get("value") == 1.5, f"[{label}] body line_spacing value should be 1.5"
        else:
            assert ls == 1.5, f"[{label}] body line_spacing should be 1.5"
