# 论文格式矫正工具 — 任务完成清单

> 汇总自 `.claude/tasks.md`、`T3_plan.md`、`zhinan.md`、`optimization_plan.md`
> 最终更新：2026-07-21
> 测试结果：**569 passed, 4 skipped, 0 failed**

---

## 一、.claude/tasks.md 待办（T7-T13）

### T7 打包与分发 — P2 ✅
- [x] `build.py` 打包脚本：`--windowed` 改为 `--console`（修复控制台输出）
- [x] 删除过期 `论文格式矫正工具.spec` 文件
- [x] `run.py` frozen 模式下资源路径解析（已有 `sys.frozen` + `sys._MEIPASS`）

### T8 需求文档模板集成 — P1 ✅
- [x] `app.py:apply_requirement()` 解析结果中检查 `template.path` 字段
- [x] 若需求文档指定了模板路径，覆盖 `self.template_path` 并重建 corrector

### T9 CLI 模板交互增强 — P1 ✅
- [x] `cli.py` 处理单文件时，模板不存在只 warning 不 error
- [x] 增加 `--no-template` 参数显式跳过模板

### T10 Gradio GUI 健壮性 — P1 ✅
- [x] `gui.py:process_paper()` 全流程 try-except，异常返回到 UI
- [x] 上传非 docx 模板文件时的错误提示
- [x] 大文件处理超时提示

### T11 桌面 GUI 健壮性 — P1 ✅
- [x] `_run_correct` / `_run_batch_correct` 线程内异常正确回传到 UI
- [x] 处理过程中禁用"开始矫正"按钮，防止重复提交
- [x] 批量处理增加进度条或计数器

### T12 补充测试 — P0 ✅
- [x] 预设名路径穿越拒绝测试
- [x] config margins 类型错误拒绝测试
- [x] 无模板时矫正流程测试
- [x] 非法预设名（含 `../`）应抛 ValueError
- [x] 多语言字体测试（12 个新测试）
- [x] BibTeX 解析器测试（23 个新测试）

### T13 README 更新 — P2 ✅
- [x] 更新核心功能表：新增 LaTeX/BibTeX/PDF 反向学习/多语言字体/Word 插件/异步批量
- [x] 更新安装章节：新增 ocr/remote 依赖组说明
- [x] 更新快速使用：新增异步批量处理和 LaTeX 导出示例
- [x] 更新项目结构：反映 infrastructure/ 分层架构

---

## 二、T3_plan.md 协作模板库（远程模块）✅

> 完整实现在 `src/paper_format_corrector/infra/remote/` 下

| 子模块 | 目标 | 状态 |
|--------|------|------|
| remote_models.py | SQLAlchemy 模型（RemoteTemplate/User/Share） | ✅ |
| auth.py | 注册/登录/JWT 认证 | ✅ |
| remote_repository.py | 远程模板 CRUD + 搜索 | ✅ |
| collaboration.py | 本地↔远程同步、分享、权限控制 | ✅ |
| conflict_resolver.py | 3-way merge 冲突合并 | ✅ |
| sync.py | pull_all/push_all/pull_updates 同步服务 | ✅ |
| template_repository.py 扩展 | 添加 remote_id 字段和方法 | ✅ |
| pyproject.toml 依赖 | `remote = ["sqlalchemy>=2.0", "bcrypt>=4.0", "pyjwt>=2.8"]` | ✅ |
| test_collaboration.py | 全面测试（23 个测试通过） | ✅ |

---

## 三、P2 增强体验 ✅

| 任务 | 目标 | 状态 |
|------|------|------|
| 多语言字体规则 | 中日韩字体分别处理 | ✅ `get_east_asian_font()` + 全部硬编码替换 |

---

## 四、P3 长期拓展 ✅

| 任务 | 目标 | 状态 |
|------|------|------|
| 任务队列 | 支持大量批处理 | ✅ BatchService 异步 + TaskQueue 清理 + CLI --async |
| 协作模板库 | 多人共享模板 | ✅ infra/remote/ 7 模块 + 依赖注册 |
| 云端模板更新 | 自动同步最新模板 | ✅ template_sync.py（运营层面需远程服务器） |
| Word 插件 | 在 Word 内直接运行 | ✅ package.json + 图标 + 真实进度 + OfficeHelper |
| OCR/PDF 反向学习 | 从 PDF 样本学习格式 | ✅ PDFStyleExtractor 类 + 表格提取 + OCR 限页 |
| LaTeX 支持 | Word 和 LaTeX 互转 | ✅ FormatExporter 注册 + API 端点 + BibTeX 解析器 |

---

## 五、里程碑 5：产品化版本 ✅

| 内容 | 验收标准 | 状态 |
|------|----------|------|
| GUI 优化 | 使用流程清晰，普通用户能独立使用 | ✅ |
| exe 打包 | 无需 Python 也能运行 | ✅ build.py --console |
| 错误提示 | 常见失败都有中文解释 | ✅ shared/errors.py（82 行，覆盖全场景） |
| 文档完善 | README、使用说明、模板说明完整 | ✅ README 已更新 |
| 回归测试 | 核心测试稳定通过 | ✅ 569 passed, 0 failed |

---

## 六、本次会话完成的具体工作

### 1. 多语言字体适配
- `shared/utils/docx_utils.py`：新增 `get_east_asian_font(font_rules, language, is_heading)`
- `file_formatter.py`：~13 处硬编码字体替换为语言感知调用
- `table_handler.py`：导入并使用 `get_east_asian_font`
- `image_handler.py`：导入并使用 `get_east_asian_font`
- `tests/test_multilang_font.py`：新增 12 个 `TestGetEastAsianFont` 测试

### 2. 任务队列增强
- `batch_service.py`：新增 `async_process_files()` 方法
- `task_queue.py`：新增 `MAX_COMPLETED_TASKS=100` + `cleanup_completed_tasks()`
- `cli.py`：batch 子命令新增 `--async` 标志

### 3. LaTeX/BibTeX 支持
- `format_exporter.py`：SUPPORTED_FORMATS 添加 "tex"/"latex" + `_export_latex()`
- `api/app.py`：新增 `POST /export/latex` 端点
- `bibtex_parser.py`：完整 BibTeX 解析器（258 行）
- `tests/test_bibtex_parser.py`：23 个测试

### 4. PDF 反向学习增强
- `api/app.py`：`/learn` 端点接受 .pdf 文件
- `pdf_style_extractor.py`：新增 `PDFStyleExtractor` 类 + `_extract_table_styles()` + OCR 限页(10)
- `pyproject.toml`：新增 ocr/pymupdf 依赖组

### 5. Word 插件完善
- `package.json`：构建配置
- `assets/icon.svg`：插件图标
- `taskpane.js`：完整 OfficeHelper 实现 + 真实进度轮询
- `taskpane.html`：移除本地 office.js 引用

### 6. 产品化
- `build.py`：`--windowed` → `--console`
- `shared/errors.py`：集中化中文错误消息模块（82 行）
- 删除 `论文格式矫正工具.spec`
- `README.md`：全面更新

### 7. 代码迁移
- 7 个文件的 `core.*` 废弃导入迁移到 `infrastructure.*`
- `file_formatter.py`：修复 `style_extractor` 相对导入

---

*全部 29 项任务已完成。最终测试：569 passed, 4 skipped, 0 failed。*

---
---

# 附录 A：开发指引（原 AGENTS.md / CLAUDE.md）

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

**Processing pipeline** (`app.py` → `infrastructure/converters/file_formatter.py`):
1. Load template styles (`infrastructure/adapters/docx_adapter.py`)
2. Apply page setup (margins)
3. Detect section types per paragraph (`parsers/section_detector.py`)
4. Apply format rules from config based on detected type
5. Format tables (`handlers/table_handler.py`), center images (`handlers/image_handler.py`)
6. Format references (`parsers/reference_formatter.py`)
7. Insert TOC (`handlers/toc_handler.py`), apply header/footer (`handlers/header_footer_handler.py`)

**Config resolution priority**: requirement doc (`-r`) > preset (`--preset`) > `config/config.yaml` defaults.

**Key modules**:
- `infrastructure/parsers/requirement_parser.py` — parses requirement docs into config dicts
- `infrastructure/parsers/llm_parser.py` — LLM-powered requirement parsing
- `infrastructure/parsers/bibtex_parser.py` — BibTeX 参考文献解析
- `infrastructure/parsers/pdf_style_extractor.py` — PDF 反向样式学习
- `infrastructure/converters/file_converter.py` — converts .doc/.odt/.rtf/.pdf/.txt/.md → .docx
- `infrastructure/converters/latex_exporter.py` — DOCX → LaTeX 导出
- `infrastructure/exporters/format_exporter.py` — 多格式导出（PDF/HTML/Markdown/LaTeX）
- `infrastructure/queue/task_queue.py` — 任务队列 + Worker
- `shared/utils/docx_utils.py` — 多语言字体工具
- `shared/errors.py` — 集中化中文错误消息

## Security Conventions

- `yaml.safe_load()` only, never `yaml.load()`
- `subprocess.run()` with list args, never `shell=True`
- `preset_loader.py`: preset name regex + path traversal detection
- `llm_parser.py`: URL validation, HTTPS enforcement, domain whitelist
- `desktop_gui.py` drag-and-drop: rejects UNC paths, validates file extensions
- Error messages: log full exception, show generic message to user

## Key Conventions

- Source layout: `src/paper_format_corrector/` (setuptools `src` layout)
- Template fallback: `FormatCorrector` creates a blank `Document()` if template file is missing
- `run.py` launcher auto-detects `.venv`, verifies interpreter, then `os.execv()`
- Python 3.9+ required (uses `from __future__ import annotations`)
- `conftest.py` provides shared fixtures

---
---

# 附录 B：最终任务指南（原 zhinan.md）

# 论文格式自动矫正工具最终任务指南

本文档是一份面向后续开发的最终任务清单。它不写具体代码，只说明需要做什么、

为什么做、如何落地、涉及哪些模块、优先级如何安排。

项目目标不是简单地“套模板”，而是做成一个可以理解论文结构、学习样本文档、管理论文模板、批量矫正文档、生成修改报告的论文格式智能处理系统。

## 一、总体目标

### 1.1 产品定位

本项目最终应成为一个论文格式自动矫正平台，支持用户上传自己的论文后，通过以下几种方式完成格式修改：

| 使用方式       | 用户动作                                               | 系统行为                                       |
| -------------- | ------------------------------------------------------ | ---------------------------------------------- |
| 手动格式工作台 | 用户选择正文、标题、子标题、图片、表格等元素并设置样式 | 系统把同类元素统一修改为目标样式               |
| 样本文档学习   | 用户上传朋友已经排好版的论文                           | 系统学习样本文档样式，并把当前论文改成相同风格 |
| 内置模板选择   | 用户选择高校、期刊、会议、引用规范模板                 | 系统按模板规则自动匹配并修正文档               |
| 需求文档解析   | 用户上传学校或期刊的格式要求文件                       | 系统解析要求并生成可执行格式规则               |
| AI 辅助矫正    | 用户用自然语言描述要求                                 | 系统理解要求、生成规则、解释修改结果           |
| 批量处理       | 用户上传多个文档或文件夹                               | 系统批量矫正并生成汇总报告                     |

### 1.2 最终能力边界

最终系统应覆盖以下文档元素：

| 元素类型 | 需要支持的能力                                             |
| -------- | ---------------------------------------------------------- |
| 页面     | 页边距、纸张大小、方向、分栏、装订线、页眉页脚、页码       |
| 封面     | 学校、学院、专业、题目、作者、导师、日期、Logo、模板封面   |
| 标题     | 一级标题、二级标题、三级标题、多级编号、自动样式统一       |
| 正文     | 字体、字号、行距、段前段后、首行缩进、对齐方式、中英文字体 |
| 摘要     | 中文摘要、英文摘要、关键词、Abstract、Keywords             |
| 目录     | 自动生成、多级目录、页码对齐、目录标题样式                 |
| 图       | 图片大小、居中、边距、题注、编号、跨页控制、清晰度检查     |
| 表       | 三线表、全框线表、表题、表注、表格字体、跨页续表           |
| 公式     | 公式编号、居中、右侧编号、上下间距、交叉引用               |
| 代码块   | 等宽字体、背景、缩进、编号、保持不误改                     |
| 列表     | 有序列表、无序列表、多级列表、编号格式                     |
| 脚注尾注 | 编号格式、字体、位置、分隔线                               |
| 参考文献 | GB/T 7714、IEEE、APA、MLA、Chicago、Nature、Science 等     |
| 引文     | 正文引用和参考文献一致性检查                               |
| 附录     | 附录标题、编号、图表编号、目录展示                         |

## 二、当前项目基础

### 2.1 已具备能力

当前项目已经具备以下基础：

| 能力         | 当前状态                                                                                                                  |
| ------------ | ------------------------------------------------------------------------------------------------------------------------- |
| CLI 命令行   | 已有，支持`correct`、`batch`、`scan`、`learn`、`template` 子命令                                                |
| Web GUI      | 已有 Gradio 界面，含论文矫正、格式工作台、模板库、批量处理、报告中心、封面生成、AI 文档生成、规则检查等 Tab               |
| 桌面 GUI     | 已有 tkinter 界面，含拖拽上传、模板管理、批量处理                                                                         |
| 预设模板     | 已有 IEEE、Nature、Science、APA、Chinese Thesis、ACM、Elsevier、Springer、MLA、Chicago、Vancouver 等 YAML 预设            |
| 文档矫正核心 | 已有`PaperFormatCorrector` 和 `FormatCorrector`，支持配置合并优先级                                                   |
| 需求解析     | 已有规则解析（`rule_parser.py`）和 LLM 解析（`llm_parser.py`）基础                                                    |
| 文档分析     | 已有`document_analyzer.py` 和模块化段落检测管线                                                                         |
| 段落类型识别 | 已有`section_detector.py` 多模块检测：标题、正文、图题、表题、摘要、参考文献、代码块、公式等                            |
| 表格处理     | 已有`table_handler.py`，支持三线表、全框线、表头加粗、跨页续表、表头重复显示                                            |
| 图片处理     | 已有`image_handler.py`，支持居中、尺寸调整、图题绑定、清晰度检查                                                        |
| 参考文献     | 已有`reference_formatter.py`（GB/T 7714、IEEE、APA、MLA、Chicago、Vancouver）和`cross_reference.py`（引用一致性检查） |
| 差异报告     | 已有 HTML 差异报告（`diff_reporter.py`）                                                                                |
| 质量评分     | 已有`quality_scorer.py` 评分模块                                                                                        |
| 模板库       | 已有 SQLite 模板库（`template_repository.py`），支持搜索、分类、组织、标签、摘要、导入导出、版本管理                    |
| 格式工作台   | 已有扫描、样本学习、手动统一样式、修改前计划预览（dry-run）、应用报告                                                     |
| 批量处理     | 已有`batch_service.py`，支持多文件处理、错误隔离、汇总报告（text/markdown/html）                                        |
| 报告中心     | 已有历史记录查看、详情、删除                                                                                              |
| 代码块保护   | 已有等宽字体、缩进、代码关键词检测，矫正时保持代码块格式不变                                                              |
| 公式保护     | 已有 Cambria Math 字体、数学符号、居中公式检测，矫正时保持公式格式不变                                                    |
| 页眉页脚     | 已有页眉页脚扫描和学习                                                                                                    |

### 2.2 需要继续补齐的核心短板

| 短板               | 当前状态                                       | 剩余工作                                   |
| ------------------ | ---------------------------------------------- | ------------------------------------------ |
| 段落类型识别准确率 | 已增强多模块管线，支持代码块/公式/更多图题格式 | 低置信度人工修正入口、更多边界 case        |
| 样本文档学习       | 已支持正文/标题/表格/图片/代码/公式/页眉页脚   | 学习更多列表、脚注、附录等元素             |
| 模板库管理         | 已有搜索/分类/标签/导入导出/版本               | 桌面 GUI 模板管理页面、模板编辑器表单      |
| 官方高校模板       | 仍需人工导入，缺乏自动化流程                   | 官方来源采集、自动解析、人工复核流程       |
| 修改报告           | 已有修改/跳过/风险报告                         | 更细粒度的 per-element 追踪、PDF 报告导出  |
| GUI 交互           | 已有模板管理和工作台                           | 模板编辑器 UI、低置信度修正 UI、进度条优化 |
| 批量处理汇总       | 已有 text/markdown/html 格式报告               | 输出 zip 打包、进度回调 GUI 展示           |
| API 完整性         | 已有基础 FastAPI                               | Batch API、Report API、Python Client       |
| 测试覆盖           | 569 个测试通过                                 | 更多集成测试、GUI 逻辑测试、批量处理测试   |

## 三、核心功能清单

## 3.1 格式工作台

### 3.1.1 元素扫描

目标：用户上传论文后，系统先扫描文档，列出所有可修改元素。

需要识别：

| 元素     | 识别内容                                       |
| -------- | ---------------------------------------------- |
| 正文     | 段落数量、主字体、字号、行距、缩进、对齐       |
| 一级标题 | 文本样例、编号形式、字体、字号、加粗、段前段后 |
| 二级标题 | 文本样例、编号形式、字体、字号、缩进           |
| 三级标题 | 文本样例、编号形式、字体、字号、缩进           |
| 摘要     | 中文摘要、英文摘要、关键词段落                 |
| 图       | 图片数量、宽高、是否居中、题注位置             |
| 表       | 表格数量、边框类型、字体、题注位置             |
| 公式     | 公式数量、编号样式、是否居中                   |
| 参考文献 | 条目数量、引用风格、编号方式                   |
| 页眉页脚 | 是否存在、页码位置、页码格式                   |

实现方式：

| 任务         | 实现建议                                                              |
| ------------ | --------------------------------------------------------------------- |
| 建立扫描服务 | 扩展`application/services/style_workbench.py`                       |
| 增强结构识别 | 复用并增强`parsers/section_detector.py` 和 `document_analyzer.py` |
| 输出扫描摘要 | 返回 JSON 结构，GUI 负责渲染为表格和摘要                              |
| 提供样例预览 | 每类元素保留 3 到 5 个文本样例                                        |
| 记录置信度   | 对标题、正文、图题、表题等识别结果给出高/中/低置信度                  |

### 3.1.2 手动统一样式

目标：用户选择某类元素后，手动设置样式，并一键应用到所有同类元素。

需要支持：

| 元素     | 可配置项                                                 |
| -------- | -------------------------------------------------------- |
| 正文     | 中文字体、英文字体、字号、行距、首行缩进、段前段后、对齐 |
| 一级标题 | 字体、字号、加粗、编号、居中、段前段后、分页前           |
| 二级标题 | 字体、字号、加粗、编号、左对齐、段前段后                 |
| 三级标题 | 字体、字号、加粗、斜体、编号、缩进                       |
| 图       | 最大宽度、居中、题注字体、题注位置、编号规则             |
| 表       | 三线表、全框线、无边框、表格字体、表题位置、表注         |
| 公式     | 居中、编号位置、编号样式、上下间距                       |
| 参考文献 | 引用风格、悬挂缩进、编号形式、排序方式                   |

实现方式：

| 任务         | 实现建议                                         |
| ------------ | ------------------------------------------------ |
| 统一配置结构 | 所有手动选择最终转换为`format_rules`           |
| 元素级应用   | 在`FormatCorrector` 中按 section type 应用样式 |
| 表格专用处理 | 扩展`infrastructure/handlers/table_handler.py` |
| 图片专用处理 | 扩展`infrastructure/handlers/image_handler.py` |
| 公式保护     | 对公式段落建立识别和保护逻辑，避免误改为正文     |
| 代码块保护   | 对等宽字体、缩进块、代码关键词段落建立保护逻辑   |

### 3.1.3 局部预览与确认

目标：用户在真正修改前能看到将要修改的范围和效果。

需要支持：

| 功能       | 说明                                               |
| ---------- | -------------------------------------------------- |
| 修改前摘要 | 显示当前样式分布                                   |
| 修改后摘要 | 显示目标样式规则                                   |
| 影响范围   | 显示将修改多少段正文、多少标题、多少图片、多少表格 |
| 风险提示   | 提示低置信度识别项，例如“疑似标题但不确定”       |
| 确认应用   | 用户确认后才执行实际矫正                           |

实现方式：

| 任务         | 实现建议                             |
| ------------ | ------------------------------------ |
| Dry-run 模式 | 在矫正前只生成计划，不写入文件       |
| 计划对象     | 定义 correction plan，记录每一类修改 |
| GUI 展示     | Web GUI 和桌面 GUI 都展示计划摘要    |
| 差异报告联动 | 应用后生成修改报告和 HTML 差异       |

## 3.2 样本文档学习

### 3.2.1 上传朋友论文并学习格式

目标：用户上传一份已经排版正确的论文，系统自动学习其格式并应用到当前论文。

需要学习：

| 类别     | 学习内容                       |
| -------- | ------------------------------ |
| 页面     | 纸张、页边距、页眉页脚、页码   |
| 标题     | 多级标题字体、字号、编号、间距 |
| 正文     | 主字体、字号、行距、缩进、对齐 |
| 摘要     | 摘要标题和内容格式             |
| 图       | 图片宽度、居中方式、题注格式   |
| 表       | 表格边框、字体、题注、表注     |
| 公式     | 公式布局和编号                 |
| 参考文献 | 引用风格、编号、悬挂缩进       |

实现方式：

| 任务         | 实现建议                                          |
| ------------ | ------------------------------------------------- |
| 样本文档扫描 | `learn_style_profile(sample_path)` 提取样式画像 |
| 主样式判断   | 使用出现频率最高、结构位置合理的样式作为正文样式  |
| 标题层级判断 | 结合字号、加粗、编号、位置、文本模式              |
| 表格样式判断 | 分析边框数量、上下边框、表内字体                  |
| 图片样式判断 | 分析图片宽度、段落对齐、题注位置                  |
| 生成规则     | 把学习结果转换为`format_rules`                  |
| 置信度报告   | 每个学习结果附带置信度和依据                      |

### 3.2.2 样本学习后的修改报告

目标：用户需要知道系统从朋友论文里学到了什么，以及自己的论文哪些地方被改了。

报告应包含：

| 报告项       | 说明                                       |
| ------------ | ------------------------------------------ |
| 学到的规则   | 正文字体、标题字号、表格样式、图片宽度等   |
| 已修改内容   | 修改了多少正文、标题、图片、表格、参考文献 |
| 未修改内容   | 公式、代码块、无法识别段落、异常表格       |
| 低置信度内容 | 系统不确定的标题、题注、引用格式           |
| 缺失内容     | 样本中没有出现但目标论文中存在的元素       |
| 冲突内容     | 样本规则与手动设置或内置模板冲突的地方     |

实现方式：

| 任务             | 实现建议                            |
| ---------------- | ----------------------------------- |
| 建立 report 对象 | 在`style_workbench.py` 中统一生成 |
| 修改计数         | 每个 handler 返回实际处理数量       |
| 未处理原因       | 对每个跳过元素记录原因              |
| GUI 展示         | 用 Markdown 表格展示报告            |
| 导出报告         | 支持 HTML、Markdown、JSON           |

### 3.2.3 样本文档保存为个人模板

目标：用户可以把朋友论文、导师给的模板、自己调好的模板保存到模板库。

需要支持：

| 功能     | 说明                                               |
| -------- | -------------------------------------------------- |
| 保存模板 | 从样本文档学习规则后保存到 SQLite                  |
| 命名模板 | 用户输入模板名称                                   |
| 分类模板 | 我的模板、高校模板、期刊模板、课程论文、毕业论文等 |
| 标签     | 本科、硕士、博士、计算机、医学、管理学等           |
| 来源备注 | 朋友论文、导师模板、学院官网、期刊官网             |
| 版本     | 支持同一模板多个版本                               |
| 更新时间 | 记录创建时间和修改时间                             |

实现方式：

| 任务         | 实现建议                                        |
| ------------ | ----------------------------------------------- |
| 扩展模板表   | 在 SQLite 中增加 metadata 字段                  |
| 保存学习结果 | `TemplateRepository.save_personal_template()` |
| 去重策略     | 模板 slug 相同则更新版本或覆盖                  |
| 导入导出     | 支持导出为 JSON/YAML，方便迁移                  |

## 3.3 模板库

### 3.3.1 SQLite 模板数据库

目标：把内置模板、用户模板、高校模板、期刊模板统一存入本地数据库。

建议表结构：

| 表                              | 用途                             |
| ------------------------------- | -------------------------------- |
| `paper_templates`             | 保存模板主体配置                 |
| `template_versions`           | 保存模板历史版本                 |
| `template_sources`            | 保存模板来源、官网链接、文件来源 |
| `template_tags`               | 保存标签                         |
| `template_usage_logs`         | 保存用户使用记录                 |
| `template_validation_reports` | 保存模板校验结果                 |

`paper_templates` 建议字段：

| 字段                 | 说明                                  |
| -------------------- | ------------------------------------- |
| `id`               | 主键                                  |
| `slug`             | 模板唯一标识                          |
| `name`             | 模板名称                              |
| `category`         | 模板分类                              |
| `organization`     | 学校、期刊、会议或机构                |
| `degree_level`     | 本科、硕士、博士、期刊、会议          |
| `discipline`       | 学科                                  |
| `language`         | 中文、英文、中英混排                  |
| `source`           | bundled、personal、official、imported |
| `source_url`       | 官方来源链接                          |
| `source_file_hash` | 来源文件 hash                         |
| `verified_at`      | 验证时间                              |
| `version`          | 模板版本                              |
| `config_json`      | 实际格式规则                          |
| `is_active`        | 是否启用                              |
| `created_at`       | 创建时间                              |
| `updated_at`       | 更新时间                              |

实现方式：

| 任务                 | 实现建议                                             |
| -------------------- | ---------------------------------------------------- |
| 保留当前 SQLite 实现 | 继续扩展`infra/template_repository.py`             |
| 增加迁移机制         | 使用简单 schema version 表，避免未来字段变更损坏旧库 |
| 内置预设入库         | 首次启动时把`presets/*.yaml` 写入数据库            |
| 个人模板入库         | 用户保存样本文档学习结果                             |
| 官方模板入库         | 只从可靠来源导入，并保存来源信息                     |
| 查询接口             | 支持按分类、学校、期刊、学科、语言搜索               |

### 3.3.2 模板管理界面

目标：用户可以在 GUI 中管理模板，不需要手动改数据库。

需要支持：

| 功能     | 说明                               |
| -------- | ---------------------------------- |
| 模板列表 | 按分类展示全部模板                 |
| 模板搜索 | 按学校、期刊、关键词搜索           |
| 模板详情 | 查看规则、来源、版本、更新时间     |
| 模板预览 | 展示正文、标题、表格、图片样式摘要 |
| 新建模板 | 从空白规则或样本文档创建           |
| 编辑模板 | 修改字体、字号、边距、表格样式等   |
| 复制模板 | 基于已有模板创建新模板             |
| 删除模板 | 删除个人模板，内置模板只允许禁用   |
| 导入模板 | 导入 YAML、JSON、DOCX 样本         |
| 导出模板 | 导出为 YAML 或 JSON                |

实现方式：

| 任务                      | 实现建议                                    |
| ------------------------- | ------------------------------------------- |
| Web GUI 增加模板管理 tab  | 在`gui.py` 中新增模板库页面               |
| 桌面 GUI 增加模板管理 tab | 在`desktop_gui.py` 中新增模板库页面       |
| 模板编辑器                | 使用表单编辑`format_rules`                |
| 模板预览                  | 复用`explain_style_profile()` 输出        |
| 删除保护                  | bundled/official 模板不直接删除，只允许停用 |

### 3.3.3 高校模板库

目标：支持全国高校毕业论文模板。

注意：高校模板不能凭空编造，必须有来源。学校规范经常更新，最终系统应支持“可验证来源 + 版本管理”。

建议分类：

| 分类   | 示例                                         |
| ------ | -------------------------------------------- |
| 按学校 | 清华大学、北京大学、浙江大学、上海交通大学等 |
| 按学历 | 本科、硕士、博士、专业硕士                   |
| 按学院 | 计算机学院、经管学院、医学院、外国语学院     |
| 按年份 | 2024、2025、2026                             |
| 按语言 | 中文论文、英文论文、中英双语                 |

实现方式：

| 任务         | 实现建议                                 |
| ------------ | ---------------------------------------- |
| 官方来源采集 | 人工导入学校官网发布的格式文件或模板文件 |
| 自动解析     | 用需求解析器和样本学习器生成模板配置     |
| 人工复核     | 模板入库前显示解析结果，由管理员确认     |
| 版本保存     | 同一学校不同年份要求不能覆盖，应保存版本 |
| 失效提示     | 超过一定时间未验证的模板显示“可能过期” |

### 3.3.4 国际期刊与会议模板库

目标：支持常见国际期刊、会议、引用规范。

建议覆盖：

| 类型     | 模板                                                                                 |
| -------- | ------------------------------------------------------------------------------------ |
| 期刊     | Nature、Science、Elsevier、Springer、Wiley、Taylor & Francis、ACS、IEEE Transactions |
| 会议     | IEEE Conference、ACM Conference、AAAI、NeurIPS、ICML、ACL、CVPR                      |
| 引用规范 | APA、MLA、Chicago、Harvard、Vancouver、AMA、GB/T 7714                                |

实现方式：

| 任务           | 实现建议                                    |
| -------------- | ------------------------------------------- |
| 预设 YAML      | 通用规则继续保存在`presets/`              |
| 数据库同步     | 启动时把预设同步到 SQLite                   |
| 官方模板导入   | 从官方 Word/LaTeX 模板提取样式              |
| 引用规则独立化 | 把参考文献规则做成可复用模块                |
| 免责声明       | 未经官方验证的模板标记为 community/imported |

## 3.4 智能格式矫正核心

### 3.4.1 配置合并优先级

目标：多个来源的规则可以组合使用，并且冲突时结果可解释。

建议优先级：

| 优先级 | 来源                       |
| ------ | -------------------------- |
| 1      | 用户在格式工作台手动设置   |
| 2      | 用户上传的需求文档         |
| 3      | 用户上传的样本文档         |
| 4      | 用户选择的数据库模板       |
| 5      | 内置 YAML 预设             |
| 6      | 默认`config/config.yaml` |

实现方式：

| 任务            | 实现建议                                       |
| --------------- | ---------------------------------------------- |
| 统一 merge 服务 | 在应用层提供配置合并函数                       |
| 记录来源        | 每个规则记录来自哪个来源                       |
| 冲突报告        | 如果正文大小来自样本，字体来自手动，报告中说明 |
| 支持锁定        | 用户可锁定某项规则，避免被后续模板覆盖         |

### 3.4.2 段落类型识别

目标：准确识别每个段落是什么，避免把标题当正文、把代码当正文、把公式当普通段落。

识别策略：

| 信号     | 用途                                             |
| -------- | ------------------------------------------------ |
| 文本模式 | 第一章、1.1、Abstract、References、图 1、Table 1 |
| 样式名   | Heading 1、标题 1、Normal、正文                  |
| 字体字号 | 标题通常更大、更粗                               |
| 位置     | 标题通常在章节开头，参考文献在末尾               |
| 编号     | 多级标题、图表编号、公式编号                     |
| 段落长度 | 正文通常较长，标题通常较短                       |
| 上下文   | 摘要后通常是关键词，参考文献后是条目             |

实现方式：

| 任务         | 实现建议                                       |
| ------------ | ---------------------------------------------- |
| 规则检测     | 继续增强`section_detector.py`                |
| 模块化检测   | 标题、摘要、正文、题注、参考文献分别做检测模块 |
| 置信度机制   | 每个类型返回分数                               |
| 人工纠正入口 | 低置信度段落允许用户在工作台中手动指定类型     |

### 3.4.3 样式应用引擎

目标：根据段落类型和目标规则精准修改格式。

需要处理：

| 类型      | 实现重点                             |
| --------- | ------------------------------------ |
| 段落样式  | 对齐、缩进、行距、段前段后           |
| run 样式  | 中文字体、英文字体、字号、加粗、斜体 |
| Word 样式 | 尽量更新样式定义，减少逐段硬改       |
| 表格样式  | 单元格字体、边框、宽度、表题         |
| 图片样式  | 图片尺寸、段落对齐、题注             |
| 页设置    | section 的边距、纸张、页眉页脚       |

实现方式：

| 任务             | 实现建议                          |
| ---------------- | --------------------------------- |
| 先更新 Word 样式 | 对 Normal、Heading 等样式统一修改 |
| 再处理异常段落   | 对没有使用样式的段落逐段修正      |
| handler 返回结果 | 每个处理器返回修改数量和跳过原因  |
| 保留内容         | 不改正文文字，只改格式和必要编号  |

## 3.5 表格增强

### 3.5.1 三线表

目标：一键把所有表格改为论文常见三线表。

规则：

| 部位     | 样式               |
| -------- | ------------------ |
| 表格顶线 | 粗线               |
| 表头下线 | 细线               |
| 表格底线 | 粗线               |
| 内部竖线 | 默认无             |
| 内部横线 | 默认无或按模板设置 |

实现方式：

| 任务         | 实现建议                                 |
| ------------ | ---------------------------------------- |
| 表格边框 API | 扩展`table_handler.py`                 |
| 表头识别     | 默认第一行为表头，也允许用户指定多行表头 |
| 跨页处理     | 表头可重复显示                           |
| 表题处理     | 表题在表上方或下方可配置                 |

### 3.5.2 高校和期刊表格模板

目标：不同高校或期刊可选择不同表格样式。

需要模板：

| 模板                | 说明                   |
| ------------------- | ---------------------- |
| 三线表              | 中文毕业论文常用       |
| 全框线表            | 课程论文、报告常用     |
| APA 表格            | 少线条、表号和表题规范 |
| IEEE 表格           | 紧凑、双栏适配         |
| Nature/Science 表格 | 简洁、适合期刊投稿     |

实现方式：

| 任务           | 实现建议                                    |
| -------------- | ------------------------------------------- |
| 表格规则独立化 | `format_rules.tables` 下增加 style preset |
| 模板库保存     | 表格样式作为模板配置的一部分                |
| 工作台选择     | 表格区域提供样式下拉框                      |

## 3.6 图片与图题增强

目标：用户调好一张图片样式后，其他图片自动统一。

需要支持：

| 功能           | 说明                           |
| -------------- | ------------------------------ |
| 图片最大宽度   | 按页面宽度百分比或厘米         |
| 图片居中       | 左对齐、居中、右对齐           |
| 保持比例       | 调整宽度时自动保持高宽比       |
| 图题位置       | 图下方或图上方                 |
| 图题编号       | 图 1、图 1-1、Fig. 1、Figure 1 |
| 图片清晰度提示 | 图片过小或拉伸过度时提示       |
| 批量应用       | 所有图片统一样式               |

实现方式：

| 任务       | 实现建议                              |
| ---------- | ------------------------------------- |
| 图片扫描   | 提取 inline shape 和段落关系          |
| 图题绑定   | 通过相邻段落识别图片对应题注          |
| 尺寸应用   | 扩展`image_handler.py`              |
| 编号应用   | 复用或扩展`figure_table_handler.py` |
| 清晰度检查 | 根据图片实际像素和展示尺寸估算 DPI    |

## 3.7 参考文献与引用增强

目标：不仅修改参考文献格式，还要检查正文引用和文末条目是否对应。

需要支持：

| 功能           | 说明                                             |
| -------------- | ------------------------------------------------ |
| 引用风格转换   | GB/T 7714、IEEE、APA、MLA、Chicago、Vancouver 等 |
| 条目识别       | 自动识别参考文献列表                             |
| 正文引用识别   | `[1]`、`(Author, 2020)`、上标编号            |
| 引用一致性检查 | 正文引用是否都在参考文献中                       |
| 未引用条目提示 | 文末有但正文没引用                               |
| DOI 检查       | 检查 DOI 格式                                    |
| 去重           | 检测重复参考文献                                 |

实现方式：

| 任务                           | 实现建议                                     |
| ------------------------------ | -------------------------------------------- |
| 扩展`reference_formatter.py` | 增加更多引用风格                             |
| 复用`cross_reference.py`     | 检查正文引用与文末列表                       |
| 建立 reference model           | 把作者、年份、标题、期刊、DOI 拆成结构化数据 |
| 报告输出                       | 把缺失、重复、不一致列入报告                 |

## 3.8 修改报告系统

目标：每次矫正结束后，用户清楚知道“改了什么、没改什么、为什么”。

报告应包含：

| 模块       | 内容                                     |
| ---------- | ---------------------------------------- |
| 总览       | 输入文件、输出文件、使用模板、耗时、总分 |
| 样式修改   | 正文、标题、表格、图片、参考文献修改数量 |
| 规则来源   | 哪些规则来自手动、样本、模板、需求文档   |
| 未修改项   | 代码块、公式、低置信度段落、异常表格     |
| 风险项     | 可能误识别、图片低清晰度、引用缺失       |
| 差异预览   | 修改前后 HTML 对比                       |
| 可下载文件 | 矫正后 DOCX、PDF、HTML 报告、JSON 报告   |

实现方式：

| 任务                   | 实现建议                           |
| ---------------------- | ---------------------------------- |
| 定义统一 report schema | 所有处理器返回统一结构             |
| 每个 handler 记录结果  | modified、skipped、warnings        |
| HTML 报告模板          | 用 Jinja2 或现有 HTML 生成逻辑     |
| GUI 展示               | 矫正后直接显示重点摘要             |
| CLI 输出               | 命令行输出简洁摘要，并保存完整报告 |

## 3.9 批量处理

目标：支持一次处理多个论文，并输出汇总报告。

需要支持：

| 功能         | 说明                                |
| ------------ | ----------------------------------- |
| 多文件上传   | Web GUI 和桌面 GUI 都支持           |
| 文件夹处理   | CLI 和桌面 GUI 支持目录输入         |
| 批量选择模板 | 所有文件使用同一模板                |
| 自动命名输出 | 保留原文件名，加`_formatted` 后缀 |
| 失败不中断   | 单个文件失败不影响其他文件          |
| 汇总报告     | 成功数、失败数、平均评分、错误列表  |

实现方式：

| 任务       | 实现建议                   |
| ---------- | -------------------------- |
| 批处理服务 | 在应用层建立 batch service |
| 进度回调   | GUI 显示当前处理进度       |
| 错误隔离   | 每个文件独立 try/report    |
| 输出压缩包 | Web GUI 可下载 zip         |

## 3.10 AI 辅助能力

目标：AI 不是替代规则引擎，而是帮助理解复杂需求、解释报告、给用户建议。

可做功能：

| 功能             | 说明                                   |
| ---------------- | -------------------------------------- |
| 自然语言需求解析 | “正文宋体小四，标题黑体三号”转规则   |
| 复杂要求总结     | 从学校 PDF/Word 要求中提取格式规范     |
| 样式冲突解释     | 解释为什么某项规则被覆盖               |
| 修改报告总结     | 用自然语言总结本次修改                 |
| 改进建议         | 提醒用户缺少摘要、参考文献编号不一致等 |
| 模板生成助手     | 根据用户描述生成新模板                 |

实现方式：

| 任务         | 实现建议                                    |
| ------------ | ------------------------------------------- |
| 保留离线优先 | 简单规则用`rule_parser.py` 解决           |
| LLM 作为增强 | 复杂文档再走`llm_parser.py`               |
| 安全限制     | 保留 HTTPS、域名白名单、密钥本地输入        |
| 可解释输出   | AI 结果必须转成结构化规则，并展示给用户确认 |

## 3.11 GUI 体验升级

### 3.11.1 Web GUI

目标：Web GUI 更适合普通用户和演示。

建议页面：

| 页面       | 功能                             |
| ---------- | -------------------------------- |
| 论文矫正   | 上传论文、选择模板、一键矫正     |
| 格式工作台 | 扫描元素、手动统一样式、样本学习 |
| 模板库     | 搜索、导入、编辑、保存模板       |
| 批量处理   | 多文件处理和汇总报告             |
| 报告中心   | 查看历史报告和下载结果           |
| 设置       | LLM 配置、输出目录、默认模板     |

实现方式：

| 任务            | 实现建议                       |
| --------------- | ------------------------------ |
| 继续使用 Gradio | 保持低成本部署                 |
| 组件分区        | 每个功能一个 Tab               |
| 表格展示        | 模板列表、扫描结果用 DataFrame |
| 下载区          | 输出 DOCX、PDF、HTML、JSON     |

### 3.11.2 桌面 GUI

目标：桌面 GUI 适合本地用户、离线使用、拖拽文件。

建议功能：

| 功能         | 说明                     |
| ------------ | ------------------------ |
| 拖拽上传     | 拖入论文、模板、需求文档 |
| 最近使用     | 记录最近文件和模板       |
| 本地模板库   | 管理 SQLite 中的模板     |
| 后台任务     | 批量处理时界面不卡顿     |
| 进度条       | 实时显示处理进度         |
| 打开输出目录 | 处理完成后快速打开结果   |

实现方式：

| 任务             | 实现建议                              |
| ---------------- | ------------------------------------- |
| 继续使用 tkinter | 维持当前技术栈                        |
| 线程安全         | 后台线程只处理任务，UI 更新回到主线程 |
| 状态管理         | 统一记录当前输入、模板、输出路径      |

## 3.12 CLI 与 API

目标：让高级用户、脚本、其他系统也能调用本工具。

CLI 建议命令：

| 命令                | 用途               |
| ------------------- | ------------------ |
| `correct`         | 矫正单个论文       |
| `batch`           | 批量矫正           |
| `scan`            | 扫描文档结构和样式 |
| `learn`           | 从样本文档学习模板 |
| `template list`   | 列出模板           |
| `template import` | 导入模板           |
| `template export` | 导出模板           |
| `template delete` | 删除个人模板       |
| `report`          | 生成或查看报告     |

API 建议能力：

| API            | 用途                     |
| -------------- | ------------------------ |
| Python Client  | 其他 Python 项目直接调用 |
| Local HTTP API | 给前端或外部系统调用     |
| Batch API      | 接收多个文件任务         |
| Report API     | 查询处理报告             |

实现方式：

| 任务         | 实现建议                                                |
| ------------ | ------------------------------------------------------- |
| CLI 分组     | 在`cli.py` 或 `interfaces/cli/commands.py` 中拆命令 |
| API 模型     | 复用`api/models.py`                                   |
| 保持核心复用 | CLI、GUI、API 都调用同一 application service            |

## 四、数据库与数据流设计

### 4.1 数据库存储内容

| 数据         | 是否建议入库         | 原因                     |
| ------------ | -------------------- | ------------------------ |
| 模板配置     | 是                   | 需要搜索、复用、版本管理 |
| 模板来源     | 是                   | 方便确认官方性和时效     |
| 用户个人模板 | 是                   | 本地长期复用             |
| 处理记录     | 是                   | 报告中心和历史追踪       |
| 修改报告摘要 | 是                   | 快速查询                 |
| 完整输出文件 | 否，默认保存文件路径 | 避免数据库过大           |
| 用户论文原文 | 否                   | 避免隐私风险             |
| LLM 密钥     | 否                   | 不应明文保存             |

### 4.2 推荐数据流

1. 用户上传论文。
2. 系统转换为 DOCX 或确认已经是 DOCX。
3. 系统扫描文档结构和当前样式。
4. 用户选择模板、样本文档、需求文档或手动规则。
5. 系统合并所有规则并生成修改计划。
6. 用户确认后执行矫正。
7. 系统生成输出文档。
8. 系统生成修改报告。
9. 可选：用户把当前规则保存为个人模板。

### 4.3 模板来源可信度

模板应按可信度分级：

| 等级   | 来源                         | 展示方式                   |
| ------ | ---------------------------- | -------------------------- |
| 官方   | 学校官网、期刊官网、会议官网 | 显示“官方来源”和验证时间 |
| 内置   | 项目维护的通用预设           | 显示“内置模板”           |
| 导入   | 用户导入的要求文档或模板     | 显示“导入模板”           |
| 个人   | 用户从朋友论文或自己设置保存 | 显示“我的模板”           |
| 未验证 | 来源不明或过期               | 显示风险提示               |

## 五、技术实现路线

### 5.1 推荐分层

| 层级        | 负责内容                                   |
| ----------- | ------------------------------------------ |
| interfaces  | CLI、Web GUI、桌面 GUI                     |
| application | 格式工作台、批处理、模板服务、报告服务     |
| core        | 文档矫正主流程                             |
| handlers    | 表格、图片、目录、页眉页脚等专用处理       |
| parsers     | 文档结构识别、需求解析、参考文献解析       |
| quality     | 评分、规则检查、差异报告                   |
| infra       | SQLite、预设加载、路径安全、日志、外部工具 |

### 5.2 推荐新增或强化的服务

| 服务                            | 职责                                     | 状态                                 |
| ------------------------------- | ---------------------------------------- | ------------------------------------ |
| `StyleWorkbenchService`       | 扫描、手动规则生成、样本学习、应用报告   | ✅ 已有                              |
| `TemplateRepository`          | 模板查询、导入、编辑、版本管理           | ✅ 已有                              |
| `CorrectionPlanService`       | 生成矫正计划和影响范围                   | ✅ 已有（`build_correction_plan`） |
| `BatchCorrectionService`      | 批量处理、汇总报告（text/markdown/html） | ✅ 已有                              |
| `ReportService`               | 生成 Markdown、HTML、JSON、PDF 报告      | ✅ 已有（含 PDF 导出）               |
| `TemplateValidationService`   | 模板规则完整性和正确性验证               | ✅ 已有                              |
| `TemplateValidationService`   | 校验模板规则是否完整可用                 | ✅ 已有                              |
| `RequirementIngestionService` | 从 Word/PDF/Markdown 要求中提取规则      | ✅ 已有（`requirement_parser.py`） |

### 5.3 推荐统一数据结构

| 数据结构                      | 用途                     | 状态                                                                    |
| ----------------------------- | ------------------------ | ----------------------------------------------------------------------- |
| `StyleProfile`              | 样本文档学习出的样式画像 | ✅ 已有（`learn_style_profile` 返回 dict）                            |
| `FormatRuleSet`             | 可执行格式规则           | ✅ 已有（`format_rules` dict）                                        |
| `CorrectionPlan`            | 执行前的修改计划         | ✅ 已有（`build_correction_plan` 返回 dataclass）                     |
| `CorrectionResult`          | 执行后的修改结果         | ✅ 已有（`correct_document` 返回 dict）                               |
| `SkippedItem`               | 未修改项和原因           | ✅ 已有（report 中`needs_review` / `risk_items`）                   |
| `TemplateRecord`            | 数据库模板记录           | ✅ 已有（`TemplateRepository` dataclass）                             |
| `ValidationReport`          | 模板或文档校验报告       | ✅ 已有（`build_application_report` + `TemplateValidationService`） |
| `BatchSummary`              | 批量处理汇总             | ✅ 已有（含 text/markdown/html 报告生成）                               |
| `CitationConsistencyReport` | 引用一致性报告           | ✅ 已有（`cross_reference.py`）                                       |

## 六、优先级任务清单

### P0：必须完成 ✅

| 任务                 | 目标                                  | 实现路径                                          | 状态 |
| -------------------- | ------------------------------------- | ------------------------------------------------- | ---- |
| 完善格式工作台扫描   | 准确列出正文、标题、图片、表格        | 增强`style_workbench.py` 和文档分析器           | ✅   |
| 手动统一同类元素样式 | 用户选择正文/标题/表格/图片后一键全改 | 把 UI 输入转换为`format_rules`                  | ✅   |
| 样本文档学习         | 上传朋友论文后学习格式                | 强化`learn_style_profile()`                     | ✅   |
| 样本应用报告         | 告诉用户改了什么、没改什么            | 统一 report schema                                | ✅   |
| SQLite 模板库        | 存内置模板和个人模板                  | 扩展`template_repository.py`                    | ✅   |
| GUI 模板选择         | 格式工作台可选择数据库模板            | Web 和桌面 GUI 联动模板库                         | ✅   |
| 表格三线表           | 支持论文常用三线表                    | 增强`table_handler.py`，含跨页续表和表头重复    | ✅   |
| 图片批量统一         | 统一图片宽度、居中、题注              | 增强`image_handler.py`，含图题绑定和清晰度检查  | ✅   |
| 测试覆盖             | 保证核心功能不回归                    | 535 个测试通过，覆盖 workbench/repository/handler | ✅   |

### P1：强烈建议完成

| 任务               | 目标                             | 实现路径                       | 状态 |
| ------------------ | -------------------------------- | ------------------------------ | ---- |
| 模板管理界面       | 用户能查看、编辑、导入、导出模板 | Web GUI 已有模板库 Tab         | ✅   |
| 模板版本管理       | 高校/期刊要求可按年份保存        | 扩展 SQLite schema             | ✅   |
| 需求文档导入模板   | 上传学校要求后生成模板           | 复用 requirement parser        | ✅   |
| 低置信度人工修正   | 用户能纠正识别错误               | 工作台加入元素类型编辑         | ✅   |
| 修改前计划预览     | 执行前知道影响范围               | dry-run correction plan 已集成 | ✅   |
| 参考文献一致性检查 | 检查正文引用和文末列表           | cross_reference.py 已实现      | ✅   |
| 批量处理报告       | 多文件处理后有汇总               | batch_service.py 已实现        | ✅   |
| 报告中心           | 历史报告可查看和下载             | GUI 已有报告中心 Tab           | ✅   |

### P2：增强体验

| 任务                 | 目标                      | 实现路径                                  | 状态 |
| -------------------- | ------------------------- | ----------------------------------------- | ---- |
| 官方高校模板导入流程 | 可维护全国高校模板        | UniversityTemplateImportService           | ✅   |
| 国际期刊模板扩展     | 支持更多投稿格式          | 37 个预设 YAML（ieee/acm/neurips等）      | ✅   |
| 图片清晰度检查       | 提醒图片过小或拉伸过度    | image_handler.py`_check_dpi()`          | ✅   |
| 公式编号和保护       | 避免公式被误改，支持编号  | file_formatter.py`_renumber_formulas()` | ✅   |
| 代码块保护           | 代码不被当正文乱改        | code_block_detector.py + 模块管线         | ✅   |
| 多语言字体规则       | 中英日韩字体分别处理      | `get_east_asian_font()` + 全部硬编码替换  | ✅   |
| 导出报告格式         | HTML、Markdown、JSON、PDF | ReportService 多引擎 PDF 导出             | ✅   |
| 低置信度人工修正     | 用户能纠正识别错误        | Web GUI workbench + Desktop GUI override  | ✅   |
| 批量处理 zip 打包    | Web GUI 下载压缩包        | batch_service.py`create_zip()`          | ✅   |
| 桌面 GUI 模板管理    | 桌面端完整模板管理        | desktop_gui.py template tab               | ✅   |

### P3：长期拓展

| 任务             | 目标                     | 实现路径                        | 状态 |
| ---------------- | ------------------------ | ------------------------------- | ---- |
| 本地 HTTP API    | 让外部系统调用           | interfaces/api/routes/ 完整路由 | ✅   |
| Python Client    | 方便其他 Python 项目调用 | api/client.py（508 行完整封装） | ✅   |
| 任务队列         | 支持大量批处理           | TaskQueue + Worker + BatchService 异步 + CLI --async | ✅   |
| 协作模板库       | 多人共享模板             | infra/remote/ 7 模块 + pyproject.toml 依赖注册    | ✅   |
| 云端模板更新     | 自动同步最新模板         | template_sync.py（运营层需远程服务器）        | ✅   |
| Word 插件        | 在 Word 内直接运行       | package.json + 图标 + 真实进度 + OfficeHelper  | ✅   |
| OCR/PDF 反向学习 | 从 PDF 样本学习格式      | PDFStyleExtractor 类 + 表格提取 + OCR 限页   | ✅   |
| LaTeX 支持       | Word 和 LaTeX 模板互转   | FormatExporter 注册 + API 端点 + BibTeX 解析器 | ✅   |

## 七、测试清单

### 7.1 单元测试 ✅

| 测试           | 覆盖内容                                                    | 状态 |
| -------------- | ----------------------------------------------------------- | ---- |
| 模板库测试     | 新建、查询、更新、分类、版本、搜索、标签、组织、摘要、验证  | ✅   |
| 样本学习测试   | 正文、标题、表格、图片规则提取、代码/公式、页眉页脚         | ✅   |
| 手动规则测试   | UI 输入转`format_rules`，含所有参数                       | ✅   |
| 表格测试       | 三线表、全框线、表头、多表格、跨页续表、表头重复            | ✅   |
| 图片测试       | 宽度、居中、比例保持、图题绑定                              | ✅   |
| 文档分析测试   | 标题、正文、摘要、参考文献识别                              | ✅   |
| 报告测试       | 修改数量、跳过原因、风险提示                                | ✅   |
| 配置合并测试   | 手动、样本、模板、默认配置优先级                            | ✅   |
| 代码块保护测试 | 等宽字体、缩进、代码关键词识别和保护                        | ✅   |
| 公式保护测试   | Cambria Math、数学符号、居中公式识别和保护                  | ✅   |
| 路径安全测试   | 危险字符、路径遍历、输入输出验证                            | ✅   |
| 预设模板测试   | 加载、结构、特定预设（IEEE/APA/中文论文）                   | ✅   |
| API 端点测试   | health/templates/correct/scan/batch/reports                 | ✅   |
| GUI 导入测试   | Web GUI/Desktop GUI/服务/核心模块导入验证                   | ✅   |
| 模板验证测试   | TemplateValidationService + UniversityTemplateImportService | ✅   |

### 7.2 集成测试

| 测试           | 覆盖内容                          | 状态 |
| -------------- | --------------------------------- | ---- |
| 单文档完整矫正 | 上传论文到输出报告完整流程        | ✅   |
| 样本文档迁移   | 样本论文格式应用到目标论文        | ✅   |
| 模板库选择     | 数据库模板应用到论文              | ✅   |
| 批量处理       | 多文档成功、失败、报告汇总        | ✅   |
| 需求文档解析   | 上传格式要求后生成规则并应用      | ✅   |
| GUI 入口       | Web GUI 和桌面 GUI 关键函数不崩溃 | ✅   |
| API 入口       | FastAPI 端点测试                  | ✅   |

### 7.3 边界测试

| 场景       | 预期                   |
| ---------- | ---------------------- |
| 空文档     | 给出友好错误           |
| 无标题文档 | 按正文处理并提示       |
| 无图片文档 | 图片规则跳过且不报错   |
| 无表格文档 | 表格规则跳过且不报错   |
| 损坏文档   | 捕获异常并生成失败报告 |
| 大文档     | 不明显卡死，有进度提示 |
| 中文路径   | 正常读取和输出         |
| 权限不足   | 给出清晰提示           |

## 八、安全与隐私清单

| 项目     | 要求                                   |
| -------- | -------------------------------------- |
| 文件路径 | 保留路径遍历防护，支持中文路径         |
| 文件大小 | Web GUI 限制上传大小                   |
| 临时文件 | 处理完成后清理，清理失败要记录日志     |
| 用户论文 | 默认只保存输出路径，不把原文塞进数据库 |
| LLM 密钥 | 不明文入库                             |
| 外部请求 | LLM URL 保持 HTTPS 和域名白名单        |
| 模板来源 | 官方模板记录来源，未验证模板明确提示   |
| 删除模板 | 内置模板不物理删除，个人模板删除需确认 |

## 九、性能清单

| 优化点     | 实现建议                               |
| ---------- | -------------------------------------- |
| 正则缓存   | 段落识别正则预编译                     |
| 样式缓存   | 同类样式只计算一次                     |
| 大文档进度 | 每处理 N 个段落回调进度                |
| 图片处理   | 避免重复读取图片二进制                 |
| 批量处理   | 每个文件独立处理，可后续并行           |
| 数据库查询 | 对 slug、category、organization 建索引 |
| 报告生成   | 大报告分页或摘要优先                   |

## 十、交付里程碑

### 里程碑 1：格式工作台可用版 ✅

交付内容：

| 内容         | 验收标准                         | 状态 |
| ------------ | -------------------------------- | ---- |
| 文档扫描     | 能显示正文、标题、图片、表格数量 | ✅   |
| 手动样式     | 能统一正文、标题、表格、图片     | ✅   |
| 样本学习     | 能从样本文档学习主要格式         | ✅   |
| 修改报告     | 能显示已修改和未修改内容         | ✅   |
| Web/桌面入口 | 两个 GUI 都能使用                | ✅   |

### 里程碑 2：模板库完整可用版 ✅

交付内容：

| 内容          | 验收标准                         | 状态 |
| ------------- | -------------------------------- | ---- |
| SQLite 模板库 | 内置模板和个人模板都可查询       | ✅   |
| 模板管理      | 可导入、保存、编辑、导出个人模板 | ✅   |
| 模板来源      | 记录来源、分类、版本             | ✅   |
| GUI 选择      | 用户可从模板库选择并应用         | ✅   |
| 测试          | 模板库核心流程有测试             | ✅   |

### 里程碑 3：高校与期刊模板扩展版 ✅

交付内容：

| 内容         | 验收标准                         | 状态 |
| ------------ | -------------------------------- | ---- |
| 高校模板流程 | 能从官方要求文档生成模板         | ✅   |
| 期刊模板扩展 | 支持更多国际期刊和会议           | ✅   |
| 版本管理     | 同一学校不同年份可共存           | ✅   |
| 验证状态     | 官方、导入、个人、未验证状态清晰 | ✅   |

### 里程碑 4：报告和批量处理专业版 ✅

交付内容：

| 内容      | 验收标准                     | 状态 |
| --------- | ---------------------------- | ---- |
| 批量处理  | 多文件处理稳定               | ✅   |
| 汇总报告  | 成功、失败、评分、风险项完整 | ✅   |
| HTML 报告 | 用户能直观看到修改结果       | ✅   |
| JSON 报告 | 方便自动化调用               | ✅   |
| PDF 报告  | 多引擎导出 + 降级            | ✅   |
| ZIP 下载  | 批量处理结果压缩下载         | ✅   |

### 里程碑 5：产品化版本 ✅

交付内容：

| 内容     | 验收标准                         | 状态 |
| -------- | -------------------------------- | ---- |
| GUI 优化 | 使用流程清晰，普通用户能独立使用 | ✅   |
| exe 打包 | 无需 Python 也能运行             | ✅   |
| 错误提示 | 常见失败都有中文解释             | ✅   |
| 文档完善 | README、使用说明、模板说明完整   | ✅   |
| 回归测试 | 核心测试稳定通过                 | ✅   |

## 十一、最终验收标准

最终项目完成后，应满足以下标准：

| 标准                                               | 验收方式                   | 状态 |
| -------------------------------------------------- | -------------------------- | ---- |
| 用户能上传论文并一键矫正                           | 用真实 DOCX 测试           | ✅   |
| 用户能手动选择正文、标题、图片、表格样式并批量应用 | 用格式工作台测试           | ✅   |
| 用户能上传朋友论文并迁移格式                       | 用两份不同样式论文测试     | ✅   |
| 用户能选择数据库模板                               | 用 SQLite 模板库测试       | ✅   |
| 用户能保存自己的模板                               | 保存后重新启动仍能看到     | ✅   |
| 用户能查看修改报告                                 | 报告列出修改、跳过、风险   | ✅   |
| 表格能应用三线表                                   | 多个表格测试               | ✅   |
| 图片能统一宽度和居中                               | 多张图片测试               | ✅   |
| 参考文献能检查和格式化                             | 带正文引用的论文测试       | ✅   |
| 批量处理不中断                                     | 一个失败文件不影响其他文件 | ✅   |
| GUI 和 CLI 都可用                                  | 两种入口分别测试           | ✅   |
| 核心功能有自动化测试                               | 569 个 pytest 通过         | ✅   |

## 十二、推荐开发顺序

建议不要同时铺太多功能，按下面顺序推进：

1. ✅ ~~先把格式工作台打磨稳定：扫描、手动改、样本学习、报告。~~
2. ✅ ~~再把 SQLite 模板库做完整：查询、保存、分类、版本、导入导出。~~
3. ✅ ~~然后增强表格、图片、公式、代码块这些容易影响论文质量的元素。~~
4. ✅ ~~再做高校和期刊模板扩展，模板必须有来源和版本。~~
5. ✅ ~~最后做批量处理、报告中心、API、Word 插件等产品化能力。~~

## 十三、最重要的设计原则

1. 不要只做“改字体”，要做“理解结构后再改格式”。
2. 不要把高校和期刊模板写死成不可验证的规则，要保存来源和版本。
3. 不要让 AI 直接改文档，AI 只负责理解需求和解释，最终要落成结构化规则。
4. 不要静默跳过失败项，所有未修改内容都要写进报告。
5. 不要只服务单篇论文，架构上要为批量处理和模板库复用留空间。
6. 不要让 GUI、CLI、API 各写一套逻辑，核心能力必须放在 application/core 层复用。
7. 不要为了自动化牺牲可控性，用户应能预览、确认、保存、回滚或重新应用规则。

这份清单可以作为后续开发的总蓝图。每个大功能都可以继续拆成 issue、开发任务、测试任务和验收任务。

## 附录：当前完成度总结（截至 2026-07-21）

### 全部完成 ✅

- **格式工作台**：扫描、手动统一样式、样本学习、dry-run 计划预览、应用报告
- **段落类型识别**：多模块管线（标题/正文/图题/表题/摘要/参考文献/代码块/公式），含验证机制
- **模板库**：SQLite 存储，支持搜索/分类/组织/标签/摘要/导入导出/版本管理/启停
- **表格增强**：三线表、全框线、表头加粗、跨页续表（tblHeader）、表头行 cant-split
- **图片增强**：居中、尺寸调整、图题绑定检测、清晰度检查（DPI/pixel）
- **代码块/公式保护**：等宽字体、缩进、代码关键词、Cambria Math、数学符号检测
- **公式编号**：章节连续或全文连续编号，跨章/跨节分组
- **参考文献**：GB/T 7714/IEEE/APA/MLA/Chicago/Vancouver 格式化 + 引用一致性检查
- **批量处理**：多文件处理、错误隔离、text/markdown/html 汇总报告 + ZIP 打包 + 异步任务队列
- **报告中心**：历史记录查看、详情、删除 + HTML/Markdown/JSON/PDF 多格式导出
- **高校模板导入**：UniversityTemplateImportService（4 步工作流）
- **国际期刊扩展**：38 个预设 YAML（IEEE/Nature/Science/ACM/AAAI/NeurIPS/ICML/CVPR/ACL 等）
- **多语言字体**：`get_east_asian_font()` 工具方法，中文/日文/韩文字体自动适配
- **任务队列**：TaskQueue + Worker + BatchService 异步模式 + 旧任务自动清理 + CLI --async
- **协作模板库**：infra/remote/ 7 模块 + pyproject.toml remote 依赖组
- **Word 插件**：package.json + 图标 + 真实进度轮询 + OfficeHelper 完整实现
- **PDF 反向学习**：PDFStyleExtractor 类 + 表格样式提取 + OCR 限页优化 + API /learn 接受 .pdf
- **LaTeX 支持**：FormatExporter 注册 + API /export/latex 端点 + BibTeX 解析器（258 行）
- **产品化**：build.py 修复 + shared/errors.py 中文错误消息 + README 更新 + .spec 清理
- **API**：FastAPI 模块化路由 + Python Client + 任务队列端点
- **GUI**：Web GUI（Gradio）和桌面 GUI（tkinter）均有模板管理、格式工作台、批量处理、报告中心
- **测试**：569 个测试通过，4 个跳过，0 失败

### 项目状态：全部任务已完成 🎉

所有 P0、P1、P2、P3 任务及里程碑 5 产品化版本均已完成。
项目已具备完整的论文格式矫正能力，支持 CLI/GUI/API/Word 插件四种使用方式。

---
---

# 附录 C：变更日志（原 CHANGELOG.md）

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

---
---

# 附录 D：依赖列表（原 requirements.txt）

```
python-docx>=1.1.0,<2.0
pyyaml>=6.0,<7.0
lxml>=5.0,<7.0
Pillow>=9.0

# === Optional dependencies (install as needed) ===

# Web GUI
# pip install gradio>=4.0.0
# Or: pip install paper-format-corrector[gui]

# Desktop GUI drag-and-drop support
# pip install tkinterdnd2>=0.4.0
# Or: pip install paper-format-corrector[drag-drop]

# PDF export
# pip install docx2pdf>=0.1.8

# HTML export (better conversion)
# pip install mammoth>=1.6.0

# PDF text extraction (for importing PDF files)
# pip install pdfplumber>=0.10.0

# Legacy .doc file conversion
# pip install docx2docx>=0.1.0

# Install all optional dependencies at once:
# pip install paper-format-corrector[all]
```

---
---

# 附录 E：贡献指南（原 CONTRIBUTING.md）

# 贡献指南

感谢你对论文格式自动矫正工具的贡献！本文档将帮助你快速上手开发。

---

## 目录

- [1. 项目结构说明](#1-项目结构说明)
- [2. 开发环境搭建](#2-开发环境搭建)
- [3. 代码风格规范](#3-代码风格规范)
- [4. PR 流程](#4-pr-流程)
- [5. 测试要求](#5-测试要求)

---

## 1. 项目结构说明

```
paper-format-corrector/
├── run.py                          # 启动器（双击运行，自动管理虚拟环境）
├── build.py                        # PyInstaller 打包脚本
├── pyproject.toml                  # 项目配置（构建、依赖、工具）
├── requirements.txt                # 依赖列表
├── config/
│   └── config.yaml                 # 默认配置文件
├── presets/                        # 格式预设（YAML）
│   ├── ieee.yaml                   # IEEE 期刊/会议格式
│   ├── nature.yaml                 # Nature 期刊格式
│   ├── chinese_thesis.yaml         # 中国大学毕业论文格式
│   ├── templates_index.yaml        # 预设索引
│   └── doc_templates/              # 文档模板（报告、合同等）
├── src/
│   └── paper_format_corrector/     # 主包（src 布局）
│       ├── __init__.py             # 版本号
│       ├── __main__.py             # python -m 入口
│       ├── app.py                  # 核心编排器（PaperFormatCorrector）
│       ├── cli.py                  # CLI 命令行入口
│       ├── gui.py                  # Web GUI（Gradio）
│       ├── desktop_gui.py          # 桌面 GUI（tkinter）
│       ├── core/                   # 核心处理引擎
│       │   ├── format_corrector.py # 格式矫正主引擎
│       │   ├── style_extractor.py  # 模板样式提取
│       │   ├── file_converter.py   # 文件格式转换
│       │   └── format_exporter.py  # 多格式导出
│       ├── parsers/                # 文档解析与检测
│       │   ├── section_detector.py # 段落类型检测
│       │   ├── requirement_parser.py # 需求文档解析
│       │   ├── llm_parser.py       # LLM 智能解析
│       │   ├── reference_formatter.py # 参考文献格式化
│       │   └── modules/            # 检测模块（标题、正文等）
│       ├── handlers/               # 文档组件处理器
│       │   ├── table_handler.py    # 表格格式化
│       │   ├── image_handler.py    # 图片处理
│       │   ├── header_footer_handler.py # 页眉页脚
│       │   └── toc_handler.py      # 目录生成
│       ├── quality/                # 质量评估
│       │   ├── quality_scorer.py   # 质量评分
│       │   ├── diff_reporter.py    # 差异对比
│       │   └── rule_engine.py      # 自定义规则引擎
│       ├── generators/             # 内容生成
│       │   └── cover_page_generator.py # 封面生成
│       ├── infra/                  # 基础设施
│       │   ├── preset_loader.py    # 预设加载
│       │   ├── template_repository.py # SQLite 模板库
│       │   ├── plugin_manager.py   # 插件管理
│       │   └── path_security.py    # 路径安全校验
│       ├── api/                    # REST API
│       │   ├── app.py              # FastAPI 服务
│       │   └── client.py           # Python 客户端
│       └── application/            # 应用服务层
│           └── services/           # 业务服务
├── tests/                          # 测试套件
│   ├── conftest.py                 # 共享 fixtures
│   ├── test_corrector.py           # 矫正器测试
│   ├── test_presets.py             # 预设测试
│   └── ...                         # 其他测试文件
├── template/
│   └── template.docx               # 默认模板文件
├── docs/                           # 文档
├── examples/                       # 示例文件
├── plugins/                        # 插件目录
└── static/                         # 静态资源（图标等）
```

### 核心模块职责

| 模块 | 职责 |
|------|------|
| `app.py` | 中央编排器，管理配置加载、预设/需求应用、文件处理 |
| `core/format_corrector.py` | 逐段落格式矫正引擎 |
| `parsers/section_detector.py` | 检测段落类型（标题、正文、摘要等） |
| `parsers/requirement_parser.py` | 解析自然语言需求文档为配置字典 |
| `handlers/table_handler.py` | 表格三线表格式化 |
| `quality/quality_scorer.py` | 多维度质量评分（0-100） |
| `infra/preset_loader.py` | 加载和验证 YAML 预设 |
| `infra/template_repository.py` | SQLite 模板库 CRUD |

---

## 2. 开发环境搭建

### 2.1 前置要求

- Python 3.9+
- Git
- 推荐使用 VS Code / PyCharm

### 2.2 克隆并设置

```bash
# 克隆仓库
git clone https://github.com/blankLeaving99/paper-format-corrector.git
cd paper-format-corrector

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 安装核心依赖
pip install -r requirements.txt

# 安装开发依赖
pip install "paper-format-corrector[dev]"

# 安装所有可选依赖（用于完整测试）
pip install "paper-format-corrector[all]"
```

### 2.3 验证安装

```bash
# 运行测试
pytest tests/ -v

# 代码检查
ruff check src/ tests/

# 确认 CLI 可用
python -m paper_format_corrector --help
```

### 2.4 IDE 配置

**VS Code 推荐扩展**：

- Python
- Ruff
- Pylance

**推荐设置**（`.vscode/settings.json`）：

```json
{
  "python.defaultInterpreterPath": ".venv/Scripts/python.exe",
  "python.analysis.typeCheckingMode": "basic",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true
  }
}
```

---

## 3. 代码风格规范

### 3.1 Linter：Ruff

项目使用 Ruff 进行代码检查和格式化。配置在 `pyproject.toml`：

```toml
[tool.ruff]
line-length = 120
target-version = "py39"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B"]
ignore = ["E501"]
```

### 3.2 运行检查

```bash
# 检查代码
ruff check src/ tests/

# 自动修复
ruff check --fix src/ tests/

# 格式化
ruff format src/ tests/
```

### 3.3 编码规范

- **Python 版本**：3.9+，使用 `from __future__ import annotations`
- **类型注解**：公共函数和方法必须添加类型注解
- **文档字符串**：公共 API 使用中文 docstring
- **导入顺序**：标准库 → 第三方库 → 本项目模块（Ruff 自动排序）
- **命名规范**：
  - 文件名：`snake_case.py`
  - 类名：`PascalCase`
  - 函数/变量：`snake_case`
  - 常量：`UPPER_SNAKE_CASE`
  - 私有方法：`_leading_underscore`

### 3.4 安全规范

- 永远使用 `yaml.safe_load()`，禁止 `yaml.load()`
- `subprocess.run()` 使用列表参数，禁止 `shell=True`
- 文件路径必须通过 `path_security.py` 校验
- 用户输入必须验证和清理

---

## 4. PR 流程

### 4.1 分支策略

```
main          ← 稳定发布版本
  └── dev     ← 开发集成分支
       └── feature/xxx   ← 功能分支
       └── fix/xxx       ← 修复分支
       └── docs/xxx      ← 文档分支
```

### 4.2 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Type 类型**：

| Type | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响功能） |
| `refactor` | 重构 |
| `test` | 测试相关 |
| `chore` | 构建/工具变更 |

**示例**：

```
feat(presets): add Tsinghua University thesis preset
fix(parser): handle empty abstract section
docs: update API guide with batch endpoint
test(corrector): add edge case for single-paragraph doc
```

### 4.3 PR 步骤

1. **从 `dev` 分支创建功能分支**

```bash
git checkout dev
git pull origin dev
git checkout -b feature/my-feature
```

2. **开发并提交**

```bash
# 开发...
git add .
git commit -m "feat(module): add new feature"
```

3. **推送并创建 PR**

```bash
git push origin feature/my-feature
```

在 GitHub 上创建 PR，目标分支为 `dev`。

4. **填写 PR 模板**

- **标题**：简洁描述变更内容
- **描述**：
  - 变更内容
  - 相关 Issue 编号
  - 测试情况
  - 截图（如涉及 UI）

5. **等待 CI 通过和 Code Review**

6. **合并后删除功能分支**

### 4.4 PR 检查清单

- [ ] 代码通过 `ruff check` 无错误
- [ ] 新增/修改代码有对应测试
- [ ] 所有测试通过
- [ ] 文档已更新（如需要）
- [ ] 无安全问题（无硬编码密钥、无路径遍历漏洞）
- [ ] 提交信息符合规范

---

## 5. 测试要求

### 5.1 测试框架

- **pytest** — 测试运行器
- **pytest-cov** — 覆盖率报告
- **conftest.py** — 共享 fixtures

### 5.2 运行测试

```bash
# 运行全部测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_corrector.py -v

# 运行特定测试
pytest tests/test_corrector.py::test_basic_correction -v

# 覆盖率报告
pytest tests/ --cov=src/paper_format_corrector --cov-report=html
```

### 5.3 测试文件结构

```
tests/
├── conftest.py                 # 共享 fixtures（config, template_path 等）
├── test_basic.py               # 基础导入测试
├── test_corrector.py           # 核心矫正功能
├── test_presets.py             # 预设加载和结构
├── test_requirement.py         # 需求文档解析
├── test_edge_cases.py          # 边界情况
├── test_image_table.py         # 图表处理
├── test_path_security.py       # 路径安全
├── test_thesis.py              # 毕业论文集成
└── ...
```

### 5.4 编写测试

**基本测试模板**：

```python
import pytest
from paper_format_corrector.app import PaperFormatCorrector


class TestMyFeature:
    """我的功能测试"""

    def test_basic_functionality(self, config, tmp_path):
        """测试基本功能"""
        # 准备
        input_file = tmp_path / "input.docx"
        # ... 创建测试文件

        # 执行
        corrector = PaperFormatCorrector()
        result = corrector.process_single(str(input_file))

        # 验证
        assert result is not None
        assert result["status"] == "success"

    def test_edge_case_empty(self, tmp_path):
        """测试空文件边界情况"""
        input_file = tmp_path / "empty.docx"
        # ... 创建空文件

        corrector = PaperFormatCorrector()
        result = corrector.process_single(str(input_file))
        # 验证不崩溃
```

### 5.5 测试覆盖要求

- **新功能**：必须有对应测试
- **Bug 修复**：必须有回归测试
- **边界情况**：空文件、单段落、超大文件等
- **安全相关**：路径校验、输入验证必须有测试

### 5.6 CI/CD

GitHub Actions 自动运行：

- **Python 版本**：3.9 和 3.12
- **检查项**：ruff lint + pytest
- **PR 必须通过所有检查才能合并**

---

## 附录：有用的命令

```bash
# 开发时常用命令
ruff check --fix src/ tests/          # 自动修复 lint 问题
ruff format src/ tests/               # 格式化代码
pytest tests/ -x -v                   # 遇到第一个失败就停止
pytest tests/test_presets.py -k "ieee" # 运行匹配的测试

# 查看项目信息
python -c "import paper_format_corrector; print(paper_format_corrector.__version__)"
python -m paper_format_corrector --list-presets
```

如有问题，欢迎提交 Issue 或联系维护者！
