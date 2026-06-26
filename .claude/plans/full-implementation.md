# 全面改进计划 — 实现所有缺失功能

## 概述

修复所有死配置、集成未用模块、实现缺失功能。涉及 8 个文件、13 个改动点。

---

## 阶段 1：修复死配置 + 集成未用模块（6 个文件）

### 1.1 `table_handler.py` — 调用 `_set_table_width`
- **行 48**: 在 `_format_table` 的 `table.alignment = CENTER` 之后，添加：
  ```python
  table_width = self.table_config.get("width")
  if table_width:
      self._set_table_width(table, table_width)
  ```

### 1.2 `figure_table_handler.py` — 使用 `caption_position`
- **行 53-58**: 在 `_handle_caption` 中读取 `caption_position` 配置
- 新增 `_validate_caption_position()` 方法，检查标题是否在正确位置（图下表上）

### 1.3 `reference_formatter.py` — 使用模板 + 内容解析
- **行 32**: `__init__` 中添加 `self.templates = ref_config.get("templates", {})`
- 新增 `_parse_reference_fields(text)` — 解析 [N]、类型标识、作者、标题、期刊等字段
- 新增 `_format_ref_by_template(ref_type, fields, num)` — 用模板渲染参考文献
- 新增 `_reformat_reference(text, num)` — 解析+重排单条参考文献
- 在 `format_references` 中，对每条参考文献调用 `_reformat_reference`

### 1.4 `style_extractor.py` — 修复 + 增强
- **行 33**: 移除错误的 `if style.font:` 守卫
- 新增 `extract_character_styles()` — 提取字符样式
- 新增 `extract_numbering_definitions()` — 提取编号定义

### 1.5 `format_corrector.py` — 集成 StyleExtractor
- 在 `__init__` 中，当有模板时实例化 `StyleExtractor`
- `_apply_page_setup`: 配置无边距时回退到模板边距
- 样式应用方法：配置缺失时回退到模板样式

### 1.6 `header_footer_handler.py` — 实现高级功能
- **行 40**: 实现 `different_odd_even`（通过 OxmlElement 设置 `evenAndOddHeaders`）
- 新增 `_resolve_header_text(text, chapter_name)` — 替换 `{chapter}` 占位符
- 新增 `_set_section_page_number_type(section, style, start)` — 设置页码格式（罗马/阿拉伯）
- 修改 `_setup_page_numbers`: 支持前置罗马+正文阿拉伯分段

---

## 阶段 2：实现缺失功能（2 个文件）

### 2.1 `format_corrector.py` — 交叉引用
- 导入并实例化 `CrossReferenceUpdater`
- 新增 `_update_cross_references(doc)` — 构建编号映射并更新引用
- 在 `correct_document` 流程中添加为第 9 步

### 2.2 `format_corrector.py` — 公式重编号
- 扩展 `_correct_formulas` 为 `_renumber_formulas`
- 跟踪每章公式计数，重写编号为 `{chapter}-{seq}` 格式
- 构建公式编号映射供交叉引用使用

### 2.3 `format_corrector.py` — 脚注处理
- 新增 `_correct_footnotes(doc)` — 遍历脚注元素，应用字体/字号格式
- 在 `correct_document` 流程中添加为第 8b 步

### 2.4 `format_corrector.py` — 分栏处理
- 新增 `_detect_and_apply_columns(section, columns_config)` — 检测/设置分栏
- 在 `_apply_page_setup` 中调用

---

## 实施顺序

```
1.1 table_handler → 1.2 figure_table_handler → 1.3 reference_formatter →
1.4 style_extractor → 1.5 format_corrector(集成) → 1.6 header_footer →
2.1 交叉引用 → 2.2 公式重编号 → 2.3 脚注 → 2.4 分栏
```

每步完成后运行 `pytest tests/ -v` 确认无回归。

## 预估代码量

- 阶段 1: ~800 行改动/新增
- 阶段 2: ~600 行改动/新增
- 总计: ~1400 行
