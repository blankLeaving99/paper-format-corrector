# AGENTS.md

This file provides guidance to AI agents working with this repository.

## Project Overview

论文格式自动矫正工具 v3.0 — A Python tool that auto-corrects academic paper formatting (fonts, headings, margins, references, figures/tables) against templates and format presets (IEEE, Nature, Science, APA, Chinese thesis). Ships with CLI, Web GUI (Gradio), Desktop GUI (tkinter), and REST API.

## Architecture (Clean Architecture + DDD)

```
interfaces → application → domain ← infrastructure
                                    ↑
                                  shared
```

Dependency flow is strictly enforced. Run `python scripts/verify_architecture.py` to check.

### Layer Responsibilities

| Layer | Path | Responsibility |
|-------|------|---------------|
| **interfaces** | `interfaces/` | CLI, Web GUI, Desktop GUI, REST API |
| **application** | `application/` | Services, Commands (CQRS), Queries, Events |
| **domain** | `domain/` | Core business logic: correction engine, document model, quality scoring, template matching |
| **infrastructure** | `infrastructure/` | External concerns: DOCX I/O, PDF extraction, LLM, storage, event bus |
| **plugins** | `plugins/` | Extensible format plugins |
| **shared** | `shared/` | Cross-cutting: errors, utilities (no internal deps) |

### Key Directories

```
src/paper_format_corrector/
├── app.py                          # Central orchestrator (PaperFormatCorrector)
├── interfaces/
│   ├── cli/main.py                 # CLI entry point
│   ├── web/app.py                  # Gradio web GUI
│   ├── desktop/app.py              # tkinter desktop GUI
│   └── api/                        # FastAPI REST API
│       ├── app.py                  # FastAPI app
│       ├── task_manager.py         # Async task queue
│       └── routes/                 # Modular route handlers
├── application/
│   ├── commands/                   # CQRS commands (write ops)
│   │   ├── correct_document.py
│   │   └── batch_process.py
│   ├── queries/                    # CQRS queries (read ops)
│   │   └── report_query.py
│   ├── events/                     # Domain events
│   │   ├── document_events.py
│   │   └── template_events.py
│   ├── batch_service.py
│   ├── report_service.py
│   ├── style_workbench.py
│   └── template_validation_service.py
├── domain/
│   ├── correction/                 # Format correction engine
│   │   ├── engine.py               # FormatCorrector
│   │   ├── extractor.py            # StyleExtractor
│   │   └── rule_parser.py
│   ├── document/                   # Document model & parsing
│   │   ├── analyzer.py
│   │   ├── cross_reference.py
│   │   ├── pdf_style_extractor.py
│   │   ├── requirement_parser.py
│   │   ├── elements/               # Table, image handlers
│   │   └── parser/                 # Section detection, BibTeX
│   │       ├── structure.py        # SectionDetector
│   │       ├── bibtex_parser.py
│   │       └── reference.py
│   ├── quality/                    # Quality scoring & diff
│   │   ├── quality_scorer.py
│   │   ├── diff_reporter.py
│   │   └── rule_engine.py
│   ├── template/                   # Template matching
│   └── repositories/               # Abstract repository interfaces
├── infrastructure/
│   ├── converters/                 # File format conversion
│   ├── exporters/                  # Format export (HTML, PDF)
│   ├── generators/                 # Cover page generation
│   ├── queue/                      # Task queue management
│   ├── remote/                     # Remote model download
│   ├── updater/                    # Auto-update
│   ├── event/bus.py                # Lightweight event bus
│   ├── preset_loader.py            # YAML preset loading
│   ├── path_security.py            # Path validation
│   ├── template_repository.py
│   └── logger.py
├── plugins/
│   ├── base.py                     # Plugin interface
│   ├── registry.py                 # Plugin registry
│   └── builtin/                    # Built-in format plugins
└── shared/
    ├── errors.py                   # Exception hierarchy
    └── docx_utils.py               # Shared DOCX utilities
```

## Commands

```bash
# Run tests
.venv\Scripts\python.exe -m pytest tests/ -v

# Run a single test file
.venv\Scripts\python.exe -m pytest tests/test_presets.py -v

# Lint
ruff check src/ tests/

# Architecture check
python scripts/verify_architecture.py

# CLI usage
python -m paper_format_corrector -f input/paper.docx --score --diff
python -m paper_format_corrector --preset ieee -f paper.docx
python -m paper_format_corrector --gui           # Web GUI
python -m paper_format_corrector --desktop-gui    # Desktop GUI

# Build exe
python build.py
```

## Config Resolution Priority

requirement doc (`-r`) > preset (`--preset`) > `config/config.yaml` defaults.
Merging is deep-recursive in `app.py:_merge_config()`.

## Presets

Located in `presets/`. Available: `ieee`, `nature`, `science`, `apa`, `chinese_thesis`, `acl`, `cvpr`, `neurips`, etc.
Each is a YAML file with `description` + `format_rules` + `auto_detect` sections.

## Security Conventions

- `yaml.safe_load()` only, never `yaml.load()`
- `subprocess.run()` with list args, never `shell=True`
- LibreOffice lookup: absolute paths first, `shutil.which()` as last fallback
- `preset_loader.py`: preset name regex + path traversal detection
- `llm_parser.py`: URL validation, domain whitelist, HTTPS enforcement
- `desktop_gui.py` drag-and-drop: rejects UNC paths, validates extensions
- Error messages: log full exception, show generic message to user

## Key Conventions

- Source layout: `src/paper_format_corrector/` (setuptools `src` layout)
- Template fallback: `FormatCorrector` creates a blank `Document()` if template file is missing
- `run.py` launcher auto-detects `.venv`, verifies interpreter, then `os.execv()` into it
- Python 3.9+ required (uses `from __future__ import annotations`)
- `conftest.py` provides shared fixtures: `config`, `template_path`, `sample_paper_path`

## CQRS Pattern (Lightweight)

- **Commands** (`application/commands/`): Write operations that change state
- **Queries** (`application/queries/`): Read operations, no side effects
- **Events** (`application/events/`): Domain occurrences for decoupled communication

Keep it simple — don't create a command for every action. Only use for significant operations.
