# 论文格式矫正工具 — 项目改进计划

## 概述

经过全面代码审查，发现 **7 个关键 Bug**、**15+ 个代码质量问题**、**大量测试覆盖空白**。本计划分 4 个阶段实施。

---

## 阶段 1：修复关键 Bug（7 个）

### 1.1 `requirement_parser.py:479` — 复制粘贴 Bug
- 问题：`"三线表" in text or "三线表" in text` 两侧条件完全相同
- 修复：第二个应改为不同关键词，如 `"三线" in text or "三线表" in text`

### 1.2 `table_handler.py:91,111,138` — 浮动 XML 元素 Bug
- 问题：当 `tbl.tblPr` 为 None 时，`OxmlElement("w:tblPr")` 创建的元素从未挂载到表格树
- 修复：改用 `tbl._new_tblPr()` 或手动 `tbl._element.insert(0, tblPr)`

### 1.3 `toc_handler.py:20` — `position` 参数被忽略
- 问题：`insert_toc(self, doc, position=0)` 接受 position 但永远插入到开头
- 修复：实现 `body.insert(position, ...)` 逻辑

### 1.4 `reference_formatter.py:100` — `ref_end_idx` 参数未使用
- 问题：参数声明但方法体内从未引用
- 修复：在循环中使用 `ref_end_idx` 作为终止条件

### 1.5 `path_security.py:17` — `.diff.html` 扩展名永远匹配不到
- 问题：`Path("x.diff.html").suffix` 返回 `.html`，不是 `.diff.html`
- 修复：改为 `.html`，或用 `str.endswith(".diff.html")` 特殊处理

### 1.6 `image_handler.py:61` — margin 为 0 时误判
- 问题：`if page_width and left_margin and right_margin` 用 truthiness 检查，0 是有效值但为 falsy
- 修复：改为 `is not None` 检查

### 1.7 `diff_reporter.py:220` — `_esc()` 缺少引号转义
- 问题：HTML 转义遗漏 `"` 字符，存在属性注入风险
- 修复：添加 `.replace('"', '&quot;')`，或统一使用共享的 `escape_html` 函数

---

## 阶段 2：代码质量提升

### 2.1 提取共享工具函数 `utils/docx_utils.py`（新建）
- **`set_east_asian_font(run, font_name)`** — 当前在 5 个文件中重复
  - `reference_formatter.py:262`
  - `table_handler.py:147`
  - `figure_table_handler.py:116`
  - `cover_page_generator.py:182`
  - `format_corrector.py:490`
- **`set_run_font(run, font_name, east_asian, size)`** — 字体设置模式重复 7+ 次
- **`ALIGN_MAP`** — 对齐映射字典在 4+ 处重复定义
- **`EMU_PER_CM = 360000`** — 魔法数字在 2 处重复
- **`escape_html(text)`** — 统一 HTML 转义（`diff_reporter._esc` + `format_exporter._escape_html`）

### 2.2 提取 `_find_libreoffice` 到 `infra/external_tools.py`（新建）
- 当前在 `file_converter.py:436` 和 `format_exporter.py:276` 重复
- 使用 `functools.lru_cache` 替代实例变量缓存

### 2.3 统一日志系统
- 将 `infra/logger.py` 改为基于 `logging` 标准库的包装
- 为所有模块添加 `logger = logging.getLogger(__name__)`
- 将关键路径的 `print()` 替换为 `logger.info/debug/warning/error`
- 优先处理：`app.py`、`cli.py`、`format_corrector.py`

### 2.4 临时文件清理
- `app.py:148-149`：diff 临时文件在异常时不清理 → 用 `try/finally`
- `format_corrector.py:85-87`：备份文件创建失败时泄漏 → 用 `try/except` 清理

### 2.5 CLI 改进
- 失败时返回非零退出码（当前永远返回 0）
- `desktop_gui` import 用 `try/except` 包裹（与 `gui` 一致）
- 模板路径空字符串检查：`corrector.template_path and Path(...).exists()`
- 目录创建延迟到实际需要时

### 2.6 硬编码值常量化
- `format_corrector.py`：默认边距 `2.54`/`3.17`、字号 `12`、行距 `1.5` → 命名常量
- `section_detector.py`：字体集合、阈值 `80`/`0.7`/`0.5`/`60`/`14`/`13` → 命名常量
- `file_converter.py`：超时 `120`/`60`、EMU `914400` → 命名常量
- `cli.py:175`：过期日期 `"2024年6月"` → 动态生成或标记为占位符

### 2.7 `compat.py` 简化
- 移除 lines 108-113 的死代码（三个分支执行相同操作）
- 考虑用 dataclass 替代字符串前缀编码严重级别

---

## 阶段 3：测试补全

### 3.1 新增测试文件
| 测试文件 | 覆盖模块 | 优先级 |
|---------|---------|--------|
| `test_cli.py` | `cli.py` — 参数解析、预设、GUI 启动 | 高 |
| `test_file_converter.py` | `file_converter.py` — 编码检测、文本转换 | 高 |
| `test_reference_formatter.py` | `reference_formatter.py` — 引用风格检测、格式化 | 高 |
| `test_llm_parser.py` | `llm_parser.py` — URL 验证（安全相关） | 高 |
| `test_diff_reporter.py` | `diff_reporter.py` — diff 逻辑、HTML 生成 | 中 |
| `test_header_footer.py` | `header_footer_handler.py` — 页眉页脚 | 中 |
| `test_toc_handler.py` | `toc_handler.py` — 目录插入 | 中 |
| `test_rule_engine.py` | `rule_engine.py` — 12 个检查器 | 中 |
| `test_quality_scorer.py` | `quality_scorer.py` — 各评分维度 | 中 |
| `test_cover_generator.py` | `cover_page_generator.py` — 封面生成 | 低 |

### 3.2 修复现有测试问题
- 移除所有测试文件中重复的 `sys.path.insert`（`conftest.py` 已处理）
- 提取 `test_corrector.py` 中 3 处重复的 `__new__` 初始化到共享 fixture
- 加强弱断言：`test_image_table.py:156,172` 的 `assert True`
- `test_thesis.py:103` 的 `assert report.get("tables_formatted", 0) >= 0`（永远为真）
- 添加缺失的 3 个预设测试（`chicago`, `mla`, `harvard`）

### 3.3 补充边界测试
- `section_detector.py`：日语/韩语检测、启发式标题、状态跟踪
- `format_corrector.py`：备份机制、dict 格式行距、多 section 文档
- `requirement_parser.py`：空文件、GBK 编码、YAML 格式需求

---

## 阶段 4：配置与构建优化

### 4.1 `pyproject.toml`
- 修复 build-backend：`setuptools.backends._legacy:_Backend` → `setuptools.build_meta`
- 添加 `project.urls`、`project.classifiers`
- 移除 ruff 的 `E501` ignore，改用行内 `# noqa`
- 添加 `[tool.ruff.lint]` 启用 `UP`（pyupgrade）和 `B`（bugbear）规则
- 添加 `addopts = "-v --tb=short"` 到 pytest 配置
- 添加 `[tool.coverage]` 配置

### 4.2 预设修复
- `ieee.yaml:115`：`title_pattern: "^.*$"` 过于宽泛 → 收紧
- `ieee.yaml:117`：Roman numeral 只到 X → 扩展
- `config.yaml:107-113`：引用模板 `[N]` 应为 `[{num}]`

---

## 实施顺序

```
阶段 1 (Bug 修复) → 阶段 2.1-2.2 (提取共享工具) → 阶段 2.3 (日志) →
阶段 2.4-2.7 (其他改进) → 阶段 3.1-3.2 (测试) → 阶段 4 (配置)
```

每个阶段完成后运行 `pytest tests/ -v` 和 `ruff check src/ tests/` 确认无回归。
