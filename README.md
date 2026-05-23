# 论文格式自动矫正工具 v3.0

基于模板和规则自动矫正 Word 论文格式的工具，支持批量处理、质量评分、差异对比、多格式导出及 Web GUI。

## 功能

- **格式自动矫正** — 字体、字号、行距、对齐、缩进、页边距等
- **标题层级识别** — 自动检测章/节/小节，应用对应的格式
- **多语言支持** — 中文/英文/日文/韩文，自动匹配字体
- **需求文档驱动** — 从 `.docx`/`.txt` 解析格式要求并自动应用
- **LLM 智能解析** — 用 OpenAI/Anthropic/Ollama 理解复杂排版需求
- **质量评分** — 矫正后对文档格式规范性打分
- **差异对比** — 生成矫正前后的 HTML 对比报告
- **多格式导出** — 支持 PDF、HTML、Markdown、TXT
- **封面生成** — 根据元数据自动生成论文封面
- **图表编号修正** — 自动编号图、表、公式，支持按章节编号
- **参考文献格式化** — GB/T 7714 国标格式
- **页眉页脚** — 自动设置页眉、页码
- **目录生成** — 自动生成/更新目录
- **Web GUI** — Gradio 可视化界面
- **批量处理** — 一键处理整个目录的文档
- **插件系统** — 自定义矫正规则

## 安装

```bash
git clone <repo-url>
cd paper-format-corrector
pip install -r requirements.txt

# 可选依赖
pip install gradio            # Web GUI
pip install docx2pdf          # PDF 导出
pip install mammoth           # HTML 导出
pip install openai anthropic  # LLM 解析
```

## 快速开始

### 目录结构

将论文 Word 文件放入 `input/`，在 `template/` 放置模板 `.docx` 文件：

```
input/
├── paper1.docx
├── paper2.docx
template/
├── template.docx
```

### 批量处理

```bash
python main.py
```

### 单个文件

```bash
python main.py -f input/paper.docx -o output/formatted.docx
```

### 质量评分

```bash
python main.py -f input/paper.docx --score
```

### 差异对比

```bash
python main.py -f input/paper.docx --diff
```

### 需求文档驱动

```bash
# 准备一个 requirement.txt/.docx，在里面描述格式要求
python main.py -r requirement.txt -f input/paper.docx
```

### LLM 智能解析

```bash
python main.py -r requirement.txt -f input/paper.docx --llm --llm-key sk-xxx
```

### 导出多格式

```bash
python main.py -f input/paper.docx --format pdf html md
```

### 生成封面

```bash
python main.py --cover title="论文题目" author="张三" college="学院" major="专业"
```

### 启动 GUI

```bash
python gui.py
```

### 自定义规则检查

```bash
python main.py -f input/paper.docx --rules my_rules.yaml
```

### 查看模板信息

```bash
python main.py --extract
```

## 配置

编辑 `config.yaml`，可配置：

| 配置项 | 说明 |
|--------|------|
| `template.path` | 模板文件路径 |
| `format_rules.font` | 中英文字体 |
| `format_rules.headings` | 标题格式（字号、加粗、对齐、行距） |
| `format_rules.body_text` | 正文格式 |
| `format_rules.margins` | 页边距 |
| `format_rules.references` | 参考文献（GB/T 7714） |
| `format_rules.figures/tables` | 图表编号格式 |
| `format_rules.header_footer` | 页眉页脚、页码 |
| `format_rules.toc` | 目录 |
| `auto_detect` | 章节、摘要、关键词等正则模式 |

## 需求文档格式

在 `requirement.txt` 中描述格式要求，支持以下语法：

```text
# 字体
中文字体：宋体
英文字体：Times New Roman
标题字体：黑体

# 字号
章标题：二号（16pt）
节标题：三号（14pt）
正文：小四（12pt）

# 行距
正文行距：1.5倍

# 页边距
上下：2.54cm
左右：3.17cm
```

## 项目结构

```
paper-format-corrector/
├── main.py                   # 主程序入口
├── gui.py                    # Web GUI (Gradio)
├── config.yaml               # 配置文件
├── format_corrector.py       # 格式矫正核心
├── format_exporter.py        # 格式导出
├── requirement_parser.py     # 需求文档解析
├── llm_parser.py             # LLM 智能解析
├── style_extractor.py        # 模板样式提取
├── quality_scorer.py         # 质量评分
├── diff_reporter.py          # 差异对比报告
├── rule_engine.py            # 自定义规则引擎
├── section_detector.py       # 章节检测
├── cover_page_generator.py   # 封面生成
├── header_footer_handler.py  # 页眉页脚
├── toc_handler.py            # 目录处理
├── reference_formatter.py    # 参考文献格式化
├── ref_auto_complete.py      # 参考文献自动补全
├── cross_reference.py        # 交叉引用
├── figure_table_handler.py   # 图表处理
├── image_handler.py          # 图片处理
├── table_handler.py          # 表格处理
├── plugin_manager.py         # 插件管理
├── logger.py                 # 日志
├── input/                    # 输入目录
├── output/                   # 输出目录
├── template/                 # 模板目录
├── tests/                    # 测试
└── requirements.txt          # 依赖
```

## 许可证

MIT
