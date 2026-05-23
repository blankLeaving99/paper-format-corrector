# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

论文格式自动矫正工具 — a Python tool that auto-corrects academic paper formatting (fonts, headings, margins, references, figures/tables) against templates and format presets (IEEE, Nature, Science, APA, Chinese thesis). Ships with two GUIs (tkinter desktop + Gradio web) and a CLI.

## Commands

```bash
# Run tests
.venv\Scripts\python.exe -m pytest tests/ -v

# Run a single test file
.venv\Scripts\python.exe -m pytest tests/test_presets.py -v

# Lint
ruff check src/ tests/

# CLI usage
python -m paper_format_corrector -f input/paper.docx --score --diff
python -m paper_format_corrector --preset ieee -f paper.docx
python -m paper_format_corrector --gui           # Web GUI
python -m paper_format_corrector --desktop-gui    # Desktop GUI

# Build exe
python build.py
```

## Architecture

Entry points: `run.py` (launcher with auto-venv setup) → `cli.py` / `gui.py` / `desktop_gui.py`. All three create a `PaperFormatCorrector` instance from `app.py`, which is the central orchestrator.

**Processing pipeline** (`app.py` → `core/format_corrector.py`):
1. Load template styles (`style_extractor.py`)
2. Apply page setup (margins)
3. Detect section types per paragraph (`parsers/section_detector.py`) — title, abstract, heading, body, reference, figure/table caption, etc.
4. Apply format rules from config based on detected type
5. Format tables (`handlers/table_handler.py`), center images (`handlers/image_handler.py`)
6. Format references (`parsers/reference_formatter.py`)
7. Insert TOC (`handlers/toc_handler.py`), apply header/footer (`handlers/header_footer_handler.py`)

**Config resolution priority**: requirement doc (`-r`) > preset (`--preset`) > `config/config.yaml` defaults. Merging is deep-recursive in `app.py:_merge_config()`.

**Key modules**:
- `parsers/requirement_parser.py` — parses natural language / table / docx requirement docs into config dicts
- `parsers/llm_parser.py` — LLM-powered requirement parsing (OpenAI/Anthropic/Ollama), with domain whitelist for SSRF protection
- `infra/preset_loader.py` — loads YAML presets from `presets/`, validates name with `^[a-zA-Z0-9_-]+$`
- `core/file_converter.py` — converts .doc/.odt/.rtf/.pdf/.txt/.md → .docx via LibreOffice or Python libs
- `infra/path_security.py` — `validate_input_path()` / `validate_output_path()` with extension whitelists
- `infra/compat.py` — dependency checker + `get_all_packages()` for installer

**GUI architecture**: Both GUIs share the same core logic. `gui.py` (Gradio) runs functions directly in request handlers. `desktop_gui.py` (tkinter) wraps processing in `threading.Thread` to avoid blocking the UI loop.

## Presets

Located in `presets/`. Available: `ieee`, `nature`, `science`, `apa`, `chinese_thesis`. Each is a YAML file with `description` + `format_rules` + `auto_detect` sections. `load_preset()` validates name against `^[a-zA-Z0-9_-]+$` and checks path containment.

## Security Conventions

- `yaml.safe_load()` only, never `yaml.load()`
- `subprocess.run()` with list args, never `shell=True`
- LibreOffice lookup: absolute paths first, `shutil.which()` as last fallback (both `file_converter.py` and `format_exporter.py`)
- `preset_loader.py`: preset name regex + path traversal detection
- `llm_parser.py`: URL validation rejects empty host, enforces HTTPS (localhost exempted), domain whitelist
- `desktop_gui.py` drag-and-drop: rejects UNC paths (`\\`), validates file extensions
- Error messages: log full exception, show generic message to user
- `gui.py`: `atexit` cleanup for temp directories, `max_file_size="50mb"` on Gradio launch

## Key Conventions

- Source layout: `src/paper_format_corrector/` (setuptools `src` layout)
- Template fallback: `FormatCorrector` creates a blank `Document()` if template file is missing
- The `run.py` launcher auto-detects `.venv`, verifies the interpreter with `--version`, then `os.execv()` into it — no manual venv activation needed
- Python 3.9+ required (uses `from __future__ import annotations` for `str | None` syntax)
- `conftest.py` provides shared fixtures: `config`, `template_path`, `sample_paper_path`, `thesis_paper_path`, `requirement_*_path`
