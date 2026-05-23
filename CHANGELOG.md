# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/).

## [3.0.0] - 2024

### Added
- Multi-format import: .docx / .doc / .odt / .rtf / .pdf / .txt / .md with auto-conversion
- Requirement document parsing: natural language, table, and mixed formats (.txt / .md / .docx / .pdf)
- LLM-powered intelligent requirement parsing (OpenAI / Anthropic / Ollama)
- Quality scoring system (0-100 score with detailed breakdown)
- Diff comparison report (HTML)
- Multi-format export: PDF, HTML, Markdown, TXT
- Cover page generator
- Figure/table auto-numbering with chapter-based and sequential modes
- Reference validation (GB/T 7714)
- Cross-reference updater (figures, tables, formulas)
- Reference auto-complete via CrossRef API
- Header/footer management
- Table of contents generation
- Desktop GUI with drag-and-drop support (tkinter + tkinterdnd2)
- Web GUI (Gradio)
- Batch processing for directories
- Plugin architecture (PluginManager)
- Custom rule engine (YAML-based)
- Multi-language support: Chinese, English, Japanese, Korean
- PyInstaller packaging (single exe)
- Path security validation

### Changed
- Complete rewrite from v2.x to modular architecture (core / handlers / parsers / quality / generators / infra)

## [1.0.2]

### Changed
- Updated README documentation

## [1.0.1]

### Added
- Initial release with basic format correction
- Template-based style extraction
- CLI interface
