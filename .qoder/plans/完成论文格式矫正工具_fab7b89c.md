# 论文格式矫正工具 — 剩余未完成任务清单

> 更新日期：2026-07-21 | 测试状态：535 passed, 4 skipped, 0 failed

## 项目总完成度

| 类别 | 已完成 | 未完成 | 完成度 |
|------|--------|--------|--------|
| P0 必须完成 | 9/9 | 0 | 100% |
| P1 强烈建议 | 8/8 | 0 | 100% |
| P2 增强体验 | 9/10 | 1 | 90% |
| P3 长期拓展 | 0/6（代码原型均有，需收尾） | 6 | 0%（原型80%） |
| 里程碑5 产品化 | 1/5 | 4 | 20% |
| T3 协作模板库 | 8/9 | 1 | 89% |

---

## 一、P2 多语言字体规则（部分完成）

**现状**：`file_formatter.py` 已有语言感知字体逻辑（zh/ja/ko 分支），但仍有约 13 处硬编码中文字体默认值（`黑体`/`宋体`）。

### 待完成项

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 1.1 | 提取统一的多语言字体工具方法 | `shared/utils/docx_utils.py` | 新增 `_get_east_asian_font(font_rules, language, is_heading)` |
| 1.2 | 替换 file_formatter.py 硬编码字体 | `infrastructure/converters/file_formatter.py` | ~13 处 `黑体`/`宋体` 改为从配置+语言参数读取 |
| 1.3 | table_handler.py 字体适配 | `infrastructure/handlers/table_handler.py` | 硬编码字体改为从配置读取 |
| 1.4 | image_handler.py 字体适配 | `infrastructure/handlers/image_handler.py` | 同上 |
| 1.5 | 补充日文/韩文测试用例 | `tests/test_multilang_font.py` | 验证 heading/abstract/table 的日韩字体 |

---

## 二、P3 任务队列（部分完成）

**现状**：`TaskQueue`（236行）+ `Worker`（162行）已实现，API 端点 5 个已集成到 `api/app.py`。

### 待完成项

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 2.1 | BatchCorrectionService 异步模式 | `application/services/batch_service.py` | 新增 `async_process_files()` 将每个文件包装为 TaskQueue 任务 |
| 2.2 | TaskQueue 旧任务自动清理 | `infrastructure/queue/task_queue.py` | 保留最近 100 个已完成任务，超出自动清理 |
| 2.3 | CLI --async 标志 | `cli.py` | `batch` 子命令增加 `--async` 标志 |
| 2.4 | 统一两套任务管理器 | `infrastructure/queue/task_queue.py` + `interfaces/api/task_manager.py` | 让 TaskManager 成为 TaskQueue 的薄封装 |
| 2.5 | 集成测试 | `tests/test_task_queue.py` | BatchCorrectionService + TaskQueue 端到端测试 |

---

## 三、P3 协作模板库（代码完成，缺依赖注册）

**现状**：`infra/remote/` 7 个模块全部实现，`template_repository.py` 已有 remote_id，23 个测试通过。

### 待完成项

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 3.1 | 添加 remote 依赖组 | `pyproject.toml` | 添加 `remote = ["sqlalchemy>=2.0", "bcrypt>=4.0", "pyjwt>=2.8"]` |

---

## 四、P3 云端模板更新（代码完成，缺运营）

**现状**：`template_sync.py`（299行）完整实现，含 `check_updates`/`pull_updates`/`auto_sync`。

### 待完成项

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 4.1 | 建立远程 manifest 服务器 | 运营工作 | 需要 GitHub 仓库或独立服务维护模板版本清单 |
| 4.2 | 配置默认 manifest URL | `config/config.yaml` | 添加 `template_sync.manifest_url` 配置项 |

> 注：此项为运营工作，非纯代码任务，当前本地功能已足够开发/演示。

---

## 五、P3 Word 插件（前端完成，缺构建和集成）

**现状**：`interfaces/word_addin/` 含 7 个文件（taskpane.js/html/css, office.js, manifest.xml, functions.html, README.md）。

### 待完成项

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 5.1 | 添加 package.json 构建系统 | `interfaces/word_addin/package.json` | devDependencies (webpack/vite)、scripts (dev/build) |
| 5.2 | 添加图标资源 | `interfaces/word_addin/assets/` | 生成 16x16/32x32/64x64 图标（manifest.xml 引用需要） |
| 5.3 | 真实进度替代模拟进度 | `interfaces/word_addin/src/taskpane.js` | 将 `setInterval` 模拟进度替换为轮询 `/tasks/{task_id}` |
| 5.4 | office.js 兼容性修复 | `interfaces/word_addin/src/office.js` | `replaceDocument()` 添加 `insertOoxml` 降级路径 |

---

## 六、P3 OCR/PDF 反向学习（代码完成，缺 API 集成）

**现状**：`pdf_style_extractor.py`（539行）完整实现，含布局分析、样式提取、OCR 支持。

### 待完成项

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 6.1 | API /learn 端点接受 .pdf | `api/app.py`（第 196 行） | 当前仅允许 .docx，需扩展支持 .pdf |
| 6.2 | 添加 PDF 表格样式提取 | `pdf_style_extractor.py` | 新增 `_extract_tables()` 利用 pdfplumber |
| 6.3 | 扩展 OCR 依赖组 | `pyproject.toml` | 添加 `ocr = ["pytesseract", "pdf2image"]`、`pymupdf = ["PyMuPDF"]` |
| 6.4 | OCR 性能优化 | `pdf_style_extractor.py` | 限制分析页数（默认前 10 页） |

---

## 七、P3 LaTeX 支持（代码完成，缺注册和集成）

**现状**：`latex_exporter.py`（252行）完整实现 DOCX→LaTeX 转换。

### 待完成项

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 7.1 | 注册 LaTeX 为 FormatExporter 标准格式 | `infrastructure/exporters/format_exporter.py` | SUPPORTED_FORMATS 添加 `"tex"`/`"latex"`，新增 `_export_latex()` |
| 7.2 | 添加 LaTeX 导出 API 端点 | `api/app.py` | 新增 `POST /export/latex` 端点 |
| 7.3 | 添加 BibTeX 解析器 | `infrastructure/parsers/bibtex_parser.py`（新建） | 解析 .bib 文件，映射到项目参考文献格式 |
| 7.4 | LaTeX 相关测试 | `tests/test_latex_export.py` | FormatExporter LaTeX 格式、API 端点、BibTeX 解析测试 |

---

## 八、里程碑 5：产品化版本

### 待完成项

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 8.1 | 修复 exe 打包配置 | `build.py` | `--windowed` 改为 `--console`（因 run.py 需要控制台交互） |
| 8.2 | 创建集中化中文错误消息模块 | `shared/errors.py`（新建） | 错误代码→中文化消息映射 + `get_error(key, **kwargs)` |
| 8.3 | 删除过期 .spec 文件 | `论文格式矫正工具.spec` | 当前文件缺少 presets/ 目录，已过时 |
| 8.4 | GUI 使用流程优化 | `gui.py` + `desktop_gui.py` | 确保普通用户能独立使用，流程清晰 |
| 8.5 | 更新 README | `README.md` | 反映最新启动流程、模板机制、可选依赖 |

---

## 九、其他遗留项

| # | 任务 | 说明 |
|---|------|------|
| 9.1 | domain 层空实现 | `domain/entities/`、`domain/events/`、`domain/services/`、`domain/value_objects/` 均为空 `__init__.py`，如需 DDD 架构需补充 |
| 9.2 | 废弃导入路径迁移 | ~8 个测试文件使用旧路径 `paper_format_corrector.parsers.X`，应更新为 `paper_format_corrector.infrastructure.parsers.X` |

---

## 执行优先级建议

```
紧急（阻塞发布）：
  8.1 exe 打包修复
  8.2 中文错误消息模块
  3.1 pyproject.toml remote 依赖

重要（提升完整性）：
  1.x 多语言字体规则收尾
  6.1 PDF 学习 API 端点
  7.1 LaTeX 注册到 FormatExporter
  2.1-2.2 任务队列异步+清理

增强（产品化）：
  5.1-5.2 Word 插件构建系统+图标
  7.3 BibTeX 解析器
  8.4-8.5 GUI 优化 + README

运营（非代码）：
  4.1-4.2 云端模板 manifest 服务器
```

---

## 依赖关系

```
阶段 A（独立，可并行）：3.1, 6.1, 7.1, 8.1, 8.2, 8.3
阶段 B（独立，可并行）：1.x, 2.1-2.5, 6.2-6.4, 7.2-7.4
阶段 C（依赖阶段B）：5.3（依赖 2.x 任务队列 API）
阶段 D（最后）：8.4, 8.5, 9.2
阶段 E（运营，非代码）：4.1-4.2
```
