# 模板开发指南

论文格式自动矫正工具 v3.0 — YAML 模板开发完整指南

---

## 目录

- [1. YAML 模板结构说明](#1-yaml-模板结构说明)
- [2. 字段详解](#2-字段详解)
- [3. 如何从学校官网提取模板](#3-如何从学校官网提取模板)
- [4. 模板校验方法](#4-模板校验方法)
- [5. 示例模板完整注释](#5-示例模板完整注释)

---

## 1. YAML 模板结构说明

### 1.1 基本结构

每个预设模板是一个 YAML 文件，包含以下顶层键：

```yaml
description: "模板描述"        # 必填，模板的文字说明

format_rules:                  # 必填，格式规则配置
  font: { ... }                # 字体设置
  headings: { ... }            # 标题格式
  body_text: { ... }           # 正文格式
  margins: { ... }             # 页边距
  abstract: { ... }            # 摘要格式
  keywords: { ... }            # 关键词格式
  title_page: { ... }          # 题目/作者格式
  references: { ... }          # 参考文献格式
  figures: { ... }             # 图格式
  tables: { ... }              # 表格式
  formulas: { ... }            # 公式格式
  code: { ... }                # 代码格式
  header_footer: { ... }       # 页眉页脚
  page_numbering: { ... }      # 页码设置
  toc: { ... }                 # 目录

auto_detect:                   # 可选，自动检测规则
  title_pattern: '...'
  chapter_pattern: '...'
  section_pattern: '...'
  subsection_pattern: '...'
  abstract_pattern: '...'
  keywords_pattern: '...'
  reference_keywords: [...]
  acknowledgment_pattern: '...'
  appendix_pattern: '...'
  figure_caption_pattern: '...'
  table_caption_pattern: '...'
  formula_pattern: '...'
```

### 1.2 文件命名规范

- 文件名仅允许 `[a-zA-Z0-9_-]` 字符
- 建议使用小写字母和下划线：`my_university.yaml`
- 加载时会校验名称正则：`^[a-zA-Z0-9_-]+$`

### 1.3 配置优先级

```
需求文档 (-r) > 预设 (--preset) > config/config.yaml 默认值
```

预设会深度合并到默认配置中，需求文档解析结果会进一步覆盖。

---

## 2. 字段详解

### 2.1 font — 字体设置

```yaml
font:
  chinese: "宋体"              # 中文正文字体
  english: "Times New Roman"   # 英文正文字体
  heading_chinese: "黑体"      # 中文标题字体
```

### 2.2 headings — 标题格式

支持三级标题：`heading1`（章标题）、`heading2`（节标题）、`heading3`（小节标题）。

```yaml
headings:
  heading1:
    font_size: 16              # 字号（pt）
    bold: true                 # 是否加粗
    italic: false              # 是否斜体
    align: "center"            # 对齐：left / center / right / justify
    space_before: 24           # 段前间距（pt）
    space_after: 18            # 段后间距（pt）
    line_spacing: 1.5          # 行距倍数
    uppercase: false           # 是否大写（IEEE 用 true）
  heading2:
    font_size: 14
    bold: true
    italic: false
    align: "left"
    space_before: 18
    space_after: 12
    line_spacing: 1.5
  heading3:
    font_size: 12
    bold: true
    italic: false
    align: "left"
    space_before: 12
    space_after: 6
    line_spacing: 1.5
```

### 2.3 body_text — 正文格式

```yaml
body_text:
  font_size: 12                # 字号（pt），小四 = 12pt
  line_spacing: 1.5            # 行距倍数
  first_line_indent: 2         # 首行缩进（字符数），0 = 不缩进
  align: "justify"             # 对齐：left / center / right / justify
```

常用字号对照：

| 中文字号 | pt 值 | 适用场景 |
|----------|-------|----------|
| 小初 | 36 | — |
| 一号 | 26 | — |
| 小一 | 24 | — |
| 二号 | 22 | 章标题 |
| 小二 | 18 | — |
| 三号 | 16 | 节标题 |
| 小三 | 15 | — |
| 四号 | 14 | 小节标题 |
| 小四 | 12 | 正文 |
| 五号 | 10.5 | 参考文献、图表标题 |
| 小五 | 9 | IEEE 正文 |

### 2.4 margins — 页边距

```yaml
margins:
  top: 2.54                    # 上边距（cm）
  bottom: 2.54                 # 下边距（cm）
  left: 3.17                   # 左边距（cm）
  right: 3.17                  # 右边距（cm）
```

常用页边距：

| 标准 | 上 | 下 | 左 | 右 |
|------|----|----|----|----|
| 中国毕业论文 | 2.54 | 2.54 | 3.17 | 3.17 |
| IEEE | 1.905 | 2.54 | 1.5875 | 1.5875 |
| APA | 2.54 | 2.54 | 2.54 | 2.54 |

### 2.5 abstract — 摘要格式

```yaml
abstract:
  title_font_size: 16          # "摘要"标题字号
  title_bold: true             # 标题是否加粗
  title_align: "center"        # 标题对齐
  content_font_size: 12        # 摘要正文字号
  content_line_spacing: 1.5    # 摘要正文行距
  content_first_line_indent: 0  # 摘要首行缩进（通常为 0）
```

### 2.6 keywords — 关键词格式

```yaml
keywords:
  label: "关键词："             # 标签文本
  font_size: 12                # 字号
  bold_label: true             # 标签是否加粗
  separator: "；"              # 关键词分隔符
```

### 2.7 title_page — 题目/作者格式

```yaml
title_page:
  title_font_size: 22          # 题目字号
  title_bold: true             # 题目是否加粗
  title_align: "center"        # 题目对齐
  author_font_size: 12         # 作者字号
  author_align: "center"       # 作者对齐
  affiliation_font_size: 10.5  # 单位字号
  affiliation_align: "center"  # 单位对齐
```

### 2.8 references — 参考文献格式

```yaml
references:
  style: "GB/T 7714"           # 格式风格：GB/T 7714 / IEEE / APA / MLA / Chicago / Vancouver
  font_size: 10.5              # 字号
  line_spacing: 1.25           # 行距
  hanging_indent: true         # 悬挂缩进
  numbering: "sequential"      # 编号方式：sequential（顺序）/ bracket（括号）
  templates:                   # 格式模板
    journal: "[{num}] {authors}. {title}[J]. {journal}, {year}, {volume}({number}): {pages}."
    book: "[{num}] {authors}. {title}[M]. {city}: {publisher}, {year}: {pages}."
    conference: "[{num}] {authors}. {title}[C]//{proceedings}. {city}: {publisher}, {year}: {pages}."
    thesis: "[{num}] {author}. {title}[D]. {city}: {university}, {year}."
    online: "[{num}] {authors}. {title}[EB/OL]. ({year}-{month}-{day})[{access_date}]. {url}."
```

模板变量说明：

| 变量 | 说明 |
|------|------|
| `{num}` | 编号 |
| `{authors}` | 作者列表 |
| `{title}` | 标题 |
| `{journal}` | 期刊名 |
| `{volume}` | 卷号 |
| `{number}` | 期号 |
| `{pages}` | 页码 |
| `{year}` | 年份 |
| `{city}` | 出版城市 |
| `{publisher}` | 出版社 |
| `{proceedings}` | 会议论文集名 |
| `{university}` | 大学名称 |
| `{url}` | 网址 |
| `{access_date}` | 访问日期 |

### 2.9 figures — 图格式

```yaml
figures:
  label: "图"                  # 标签前缀
  numbering: "chapter"         # 编号方式：chapter（图1-1）/ sequential（图1）
  separator: "-"               # 章节模式下的分隔符
  caption_position: "below"    # 标题位置：above（上方）/ below（下方）
  font_size: 10.5              # 标题字号
  align: "center"              # 对齐
```

### 2.10 tables — 表格式

```yaml
tables:
  label: "表"                  # 标签前缀
  numbering: "chapter"         # 编号方式
  separator: "-"               # 分隔符
  caption_position: "above"    # 标题位置（表标题通常在表上方）
  font_size: 10.5              # 标题字号
  header_bold: true            # 表头是否加粗
  align: "center"              # 对齐
```

### 2.11 formulas — 公式格式

```yaml
formulas:
  numbering: true              # 是否编号
  numbering_style: "paren"     # 编号样式：paren（(1-1)）/ dot（1.1）
  numbering_position: "right"  # 编号位置：right（右对齐）
  font_size: 12                # 字号
  center: false                # 公式内容是否居中
```

### 2.12 code — 代码格式

```yaml
code:
  preserve: true               # 保留原始格式，不做矫正
  force_mono: false            # 是否强制统一为等宽字体
  mono_font: "Consolas"        # 强制等宽字体时使用的字体
  mono_font_size: 10           # 强制等宽字体时使用的字号
```

### 2.13 header_footer — 页眉页脚

```yaml
header_footer:
  enabled: true                # 是否启用
  header:
    text: ""                   # 页眉文本，留空不设置，可用 {chapter} 插入章名
    font_size: 10.5
    font_name: "宋体"
    align: "center"
    bottom_border: true        # 是否有下边框
  footer:
    page_number: true          # 是否显示页码
    font_size: 10.5
    align: "center"
  different_first_page: true   # 首页不同（首页通常不显示页眉）
  different_odd_even: false    # 奇偶页不同
```

### 2.14 page_numbering — 页码设置

```yaml
page_numbering:
  enabled: true
  front_matter:
    style: "roman_lower"       # 前置页页码样式：roman_lower（i, ii, iii）
    start: 1
  body:
    style: "arabic"            # 正文页码样式：arabic（1, 2, 3）
    start: 1
  position: "footer_center"    # 页码位置
```

### 2.15 toc — 目录

```yaml
toc:
  enabled: true                # 是否启用目录生成
  title: "目  录"              # 目录标题
  title_font_size: 16          # 标题字号
  title_bold: true             # 标题加粗
  title_align: "center"        # 标题对齐
  max_level: 3                 # 最大目录层级
  font_size: 12                # 目录正文字号
  line_spacing: 1.5            # 行距
```

### 2.16 auto_detect — 自动检测规则

```yaml
auto_detect:
  title_pattern: '^论文题目[:：]?|^题目[:：]?'
  chapter_pattern: '^第[一二三四五六七八九十百零\d]+[章部分篇]'
  section_pattern: '^\d+\.\d+'
  subsection_pattern: '^\d+\.\d+\.\d+'
  abstract_pattern: '^摘\s*要$|^Abstract$|^ABSTRACT$'
  abstract_en_pattern: '^Abstract$|^ABSTRACT$'
  keywords_pattern: '^关键词[:：]|^Key\s*[Ww]ords[:：]?'
  reference_keywords:
    - "参考文献"
    - "参考资料"
    - "References"
    - "REFERENCES"
  acknowledgment_pattern: '^致\s*谢$|^Acknowledge?ments?$'
  appendix_pattern: '^附\s*录[A-Z]?'
  figure_caption_pattern: '^图\s*\d'
  table_caption_pattern: '^表\s*\d'
  formula_pattern: '^\(?\d+[-\.]\d+\)?$'
```

每个 pattern 都是 Python 正则表达式，用于自动识别文档中不同类型的段落。

---

## 3. 如何从学校官网提取模板

### 3.1 步骤

1. **获取学校格式要求文档**
   - 从学校教务处/研究生院网站下载格式规范文件（通常是 PDF 或 Word）
   - 搜索关键词：`XX大学 毕业论文 格式要求`、`XX大学 学位论文 撰写规范`

2. **提取关键参数**
   - 字体：中文字体、英文字体、标题字体
   - 字号：各标题字号、正文字号、图表标题字号
   - 行距：正文行距、标题行距
   - 页边距：上/下/左/右
   - 格式：首行缩进、对齐方式
   - 参考文献：格式风格（GB/T 7714 等）
   - 页眉页脚：内容、格式
   - 目录：层级、格式

3. **编写 YAML 模板**
   - 参考下方「示例模板完整注释」
   - 将提取的参数填入对应字段

4. **校验模板**
   - 使用 API 的 `/templates/validate` 端点验证
   - 或在 CLI 中加载测试

### 3.2 提取技巧

- **字号**：在 Word 中选中文字，查看「字号」框中的值（如"小四"对应 12pt）
- **行距**：Word → 段落 → 行距 → 多倍行距值
- **页边距**：Word → 页面布局 → 页边距 → 自定义
- **字体**：Word → 开始 → 字体下拉框
- **缩进**：Word → 段落 → 特殊格式 → 首行缩进

### 3.3 注意事项

- 不同学院/专业可能有细微差异，以最新发布的为准
- 有些学校要求双面打印，需注意奇偶页不同
- 参考文献格式优先级：学校要求 > 国标 > 通用格式

---

## 4. 模板校验方法

### 4.1 API 校验

```bash
# 启动 API 服务
python -m paper_format_corrector.api.app

# 校验模板配置
curl -X POST http://localhost:8000/templates/validate \
  -H "Content-Type: application/json" \
  -d @my_template.yaml
```

返回示例：

```json
{
  "is_valid": true,
  "errors": [],
  "warnings": [],
  "missing_fields": [],
  "suggestions": ["建议添加 auto_detect 规则"]
}
```

### 4.2 CLI 校验

```bash
# 列出所有模板，确认新模板已加载
python -m paper_format_corrector template list

# 查看模板详情
python -m paper_format_corrector template info my_template

# 导出为 JSON 检查结构
python -m paper_format_corrector template export my_template -o check.json --format json
```

### 4.3 Python 校验

```python
from paper_format_corrector.infra.preset_loader import load_preset

try:
    config = load_preset("my_template")
    print("加载成功")
    print(f"描述: {config['description']}")
except Exception as e:
    print(f"校验失败: {e}")
```

### 4.4 校验要点

- [ ] `description` 字段已填写
- [ ] `format_rules.font` 包含中英文字体
- [ ] `format_rules.headings` 包含 heading1/2/3
- [ ] `format_rules.body_text` 包含 font_size, line_spacing, align
- [ ] `format_rules.margins` 四个边距值在合理范围（0.1-15cm）
- [ ] `format_rules.references` 包含 style 和 templates
- [ ] 正则表达式语法正确（可在 Python 中测试）

---

## 5. 示例模板完整注释

```yaml
# 示例大学硕士论文格式模板
# 基于《示例大学研究生学位论文撰写规范（2024年版）》

description: "示例大学硕士/博士学位论文格式"

format_rules:
  # ── 字体设置 ──
  font:
    chinese: "宋体"                    # 中文正文使用宋体
    english: "Times New Roman"         # 英文正文使用 Times New Roman
    heading_chinese: "黑体"            # 中文标题使用黑体

  # ── 标题格式 ──
  headings:
    heading1:                          # 一级标题（章标题，如"第一章 绪论"）
      font_size: 16                    # 三号（16pt）
      bold: true                       # 加粗
      italic: false                    # 不斜体
      align: "center"                  # 居中对齐
      space_before: 24                 # 段前 24pt
      space_after: 18                  # 段后 18pt
      line_spacing: 1.5                # 1.5 倍行距

    heading2:                          # 二级标题（节标题，如"1.1 研究背景"）
      font_size: 14                    # 四号（14pt）
      bold: true                       # 加粗
      italic: false
      align: "left"                    # 左对齐
      space_before: 18
      space_after: 12
      line_spacing: 1.5

    heading3:                          # 三级标题（小节标题，如"1.1.1 国内研究"）
      font_size: 12                    # 小四（12pt）
      bold: true                       # 加粗
      italic: false
      align: "left"
      space_before: 12
      space_after: 6
      line_spacing: 1.5

  # ── 正文格式 ──
  body_text:
    font_size: 12                      # 小四（12pt）
    line_spacing: 1.5                  # 1.5 倍行距
    first_line_indent: 2               # 首行缩进 2 字符
    align: "justify"                   # 两端对齐

  # ── 页边距 ──
  margins:
    top: 2.54                          # 上边距 2.54cm
    bottom: 2.54                       # 下边距 2.54cm
    left: 3.17                         # 左边距 3.17cm
    right: 3.17                        # 右边距 3.17cm

  # ── 摘要格式 ──
  abstract:
    title_font_size: 16                # "摘要"标题：三号
    title_bold: true
    title_align: "center"
    content_font_size: 12              # 摘要正文：小四
    content_line_spacing: 1.5
    content_first_line_indent: 0        # 摘要通常不缩进

  # ── 关键词格式 ──
  keywords:
    label: "关键词："                   # 标签文本
    font_size: 12
    bold_label: true                   # "关键词："加粗
    separator: "；"                    # 分号分隔

  # ── 题目/作者格式 ──
  title_page:
    title_font_size: 22                # 二号偏大
    title_bold: true
    title_align: "center"
    author_font_size: 12
    author_align: "center"
    affiliation_font_size: 10.5        # 五号
    affiliation_align: "center"

  # ── 参考文献格式 ──
  references:
    style: "GB/T 7714"                 # 国标格式
    font_size: 10.5                    # 五号
    line_spacing: 1.25
    hanging_indent: true               # 悬挂缩进
    numbering: "sequential"            # 顺序编号
    templates:
      journal: "[{num}] {authors}. {title}[J]. {journal}, {year}, {volume}({number}): {pages}."
      book: "[{num}] {authors}. {title}[M]. {city}: {publisher}, {year}: {pages}."
      conference: "[{num}] {authors}. {title}[C]//{proceedings}. {city}: {publisher}, {year}: {pages}."
      thesis: "[{num}] {author}. {title}[D]. {city}: {university}, {year}."
      online: "[{num}] {authors}. {title}[EB/OL]. ({year}-{month}-{day})[{access_date}]. {url}."

  # ── 图格式 ──
  figures:
    label: "图"                        # 标签前缀
    numbering: "chapter"               # 按章节编号（图1-1）
    separator: "-"                     # 章-序号 分隔符
    caption_position: "below"          # 图标题在图下方
    font_size: 10.5                    # 五号
    align: "center"

  # ── 表格式 ──
  tables:
    label: "表"
    numbering: "chapter"
    separator: "-"
    caption_position: "above"          # 表标题在表上方
    font_size: 10.5
    header_bold: true                  # 表头加粗
    align: "center"

  # ── 公式格式 ──
  formulas:
    numbering: true                    # 公式编号
    numbering_style: "paren"           # 编号样式：(1-1)
    numbering_position: "right"        # 编号右对齐
    font_size: 12

  # ── 代码格式 ──
  code:
    preserve: true                     # 保留代码块原始格式
    force_mono: false

  # ── 页眉页脚 ──
  header_footer:
    enabled: true
    header:
      text: "{chapter}"                # 页眉显示章名
      font_size: 10.5
      font_name: "宋体"
      align: "center"
      bottom_border: true              # 页眉下方有横线
    footer:
      page_number: true                # 页脚显示页码
      font_size: 10.5
      align: "center"
    different_first_page: true         # 首页不显示页眉
    different_odd_even: false

  # ── 页码设置 ──
  page_numbering:
    enabled: true
    front_matter:
      style: "roman_lower"             # 前置页用小写罗马数字（i, ii, iii）
      start: 1
    body:
      style: "arabic"                  # 正文用阿拉伯数字（1, 2, 3）
      start: 1
    position: "footer_center"

  # ── 目录 ──
  toc:
    enabled: true                      # 自动生成目录
    title: "目  录"
    title_font_size: 16
    title_bold: true
    title_align: "center"
    max_level: 3                       # 目录包含到三级标题
    font_size: 12
    line_spacing: 1.5

# ── 自动检测规则 ──
auto_detect:
  title_pattern: '^论文题目[:：]?|^题目[:：]?'
  chapter_pattern: '^第[一二三四五六七八九十百零\d]+[章部分篇]'
  section_pattern: '^\d+\.\d+'
  subsection_pattern: '^\d+\.\d+\.\d+'
  abstract_pattern: '^摘\s*要$|^Abstract$|^ABSTRACT$'
  abstract_en_pattern: '^Abstract$|^ABSTRACT$'
  keywords_pattern: '^关键词[:：]|^Key\s*[Ww]ords[:：]?'
  reference_keywords:
    - "参考文献"
    - "参考资料"
    - "References"
    - "REFERENCES"
  acknowledgment_pattern: '^致\s*谢$|^Acknowledge?ments?$'
  appendix_pattern: '^附\s*录[A-Z]?'
  figure_caption_pattern: '^图\s*\d'
  table_caption_pattern: '^表\s*\d'
  formula_pattern: '^\(?\d+[-\.]\d+\)?$'
```

---

## 附录：已有的预设模板

项目内置以下预设，可直接使用或作为参考：

| 预设名 | 说明 | 文件 |
|--------|------|------|
| `ieee` | IEEE 期刊/会议格式 | `presets/ieee.yaml` |
| `nature` | Nature 期刊格式 | `presets/nature.yaml` |
| `science` | Science 期刊格式 | `presets/science.yaml` |
| `apa` | APA 第 7 版格式 | `presets/apa.yaml` |
| `chinese_thesis` | 中国大学毕业论文格式 | `presets/chinese_thesis.yaml` |
| `tsinghua` | 清华大学 | `presets/tsinghua.yaml` |
| `peking` | 北京大学 | `presets/peking.yaml` |
| `zhejiang` | 浙江大学 | `presets/zhejiang.yaml` |
| `acm` | ACM 格式 | `presets/acm.yaml` |
| `springer` | Springer 格式 | `presets/springer.yaml` |
| `elsevier` | Elsevier 格式 | `presets/elsevier.yaml` |
| `wiley` | Wiley 格式 | `presets/wiley.yaml` |
| ... | 共 38 个预设 | `presets/*.yaml` |

查看所有预设：

```bash
python -m paper_format_corrector --list-presets
```
