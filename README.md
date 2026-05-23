# 论文格式自动矫正工具 v3.0

基于模板和规则自动矫正 Word 论文格式的工具，支持批量处理、质量评分、差异对比、多格式导出，提供桌面 GUI 和 Web GUI 两种界面。

## 功能特性

- **格式自动矫正** — 字体、字号、行距、对齐、缩进、页边距等
- **标题层级识别** — 自动检测章/节/小节，应用对应的格式
- **多语言支持** — 中文/英文/日文/韩文，自动匹配字体
- **多格式导入** — 支持 .docx / .doc / .odt / .rtf / .pdf / .txt / .md，自动转换
- **需求文档驱动** — 从 .docx / .txt / .md / .pdf 解析格式要求并自动应用
- **LLM 智能解析** — 用 OpenAI/Anthropic/Ollama 理解复杂排版需求
- **质量评分** — 矫正后对文档格式规范性打分
- **差异对比** — 生成矫正前后的 HTML 对比报告
- **多格式导出** — 支持 PDF、HTML、Markdown、TXT
- **封面生成** — 根据元数据自动生成论文封面
- **图表编号修正** — 自动编号图、表、公式，支持按章节编号
- **参考文献格式化** — GB/T 7714 国标格式
- **页眉页脚** — 自动设置页眉、页码
- **目录生成** — 自动生成/更新目录
- **双 GUI 界面** — 桌面 GUI（原生窗口，支持拖拽）+ Web GUI（浏览器）
- **批量处理** — 一键处理整个目录的文档
- **插件系统** — 自定义矫正规则

## 快速开始

### 方式一：双击运行（推荐）

直接双击项目根目录下的 `run.py`，程序会自动：
1. 检测依赖是否安装
2. 如有缺失，弹窗提示并让你选择安装位置
3. 弹出模式选择窗口，选择桌面 GUI 或 Web GUI

### 方式二：命令行

```bash
# 进入项目目录
cd paper-format-corrector

# 启动桌面 GUI（推荐，原生窗口，支持文件拖拽）
python run.py

# 命令行模式
python run.py -f input/paper.docx --score
```

## 安装

### 自动安装（推荐）

双击 `run.py`，程序会自动检测缺失依赖并提示安装，所有依赖安装到你选择的目录下的虚拟环境中，不污染系统 Python。

### 手动安装

```bash
git clone https://github.com/blankLeaving99/paper-format-corrector.git
cd paper-format-corrector

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 可选依赖
pip install tkinterdnd2        # 桌面 GUI 拖拽支持
pip install gradio             # Web GUI
pip install docx2pdf           # PDF 导出
pip install mammoth            # 更好的 HTML 导出
pip install pdfplumber         # PDF 文件导入
```

### 打包为 exe

```bash
python build.py
```

打包完成后，`dist/` 目录下的 exe 文件可以直接发给朋友使用，无需安装 Python。

## 使用说明

### 目录结构准备

将论文文件放入 `input/`，在 `template/` 放置模板 `.docx` 文件：

```
input/
├── paper1.docx
├── paper2.docx
template/
├── template.docx
```

### 桌面 GUI 功能

- **文件拖拽** — 直接拖拽文件到输入框（需安装 tkinterdnd2）
- **批量处理** — 点击"批量矫正"按钮选择多个文件
- **论文矫正** — 上传论文、选择选项、一键矫正
- **封面生成** — 填写论文信息，自动生成封面
- **规则检查** — 上传论文和规则文件，检查格式

### 命令行用法

```bash
# 批量处理 input/ 目录
python run.py

# 处理单个文件
python run.py -f input/paper.docx -o output/formatted.docx

# 质量评分
python run.py -f input/paper.docx --score

# 差异对比
python run.py -f input/paper.docx --diff

# 需求文档驱动
python run.py -r requirement.txt -f input/paper.docx

# LLM 智能解析
python run.py -r requirement.txt -f input/paper.docx --llm --llm-key sk-xxx

# 导出多格式
python run.py -f input/paper.docx --format pdf html md

# 生成封面
python run.py --cover title="论文题目" author="张三" college="学院" major="专业"

# 自定义规则检查
python run.py -f input/paper.docx --rules my_rules.yaml

# 查看模板信息
python run.py --extract
```

## 配置

编辑 `config/config.yaml`，可配置：

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

支持 `.txt` / `.md` / `.docx` / `.pdf` 格式的需求文档，示例：

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

## 支持的导入格式

| 格式 | 说明 | 依赖 |
|------|------|------|
| .docx | Word 文档（推荐） | 内置支持 |
| .doc | 旧版 Word 文档 | LibreOffice 或 docx2docx |
| .odt | OpenDocument 文档 | LibreOffice |
| .rtf | Rich Text Format | LibreOffice |
| .pdf | PDF 文档 | pdfplumber / PyMuPDF / PyPDF2 |
| .txt | 纯文本 | 内置支持 |
| .md | Markdown | 内置支持 |

## 自定义规则检查

创建 YAML 格式的规则文件：

```yaml
rules:
  - name: "参考文献不超过50篇"
    check: reference_count
    params:
      max: 50
    severity: warning

  - name: "正文字号为小四"
    check: body_font_size
    params:
      expected: 12
    severity: error
```

然后运行：

```bash
python run.py -f input/paper.docx --rules my_rules.yaml
```

## 项目结构

```
paper-format-corrector/
├── run.py                           # 启动器（双击运行）
├── build.py                         # 打包为 exe 的脚本
├── src/
│   └── paper_format_corrector/
│       ├── __init__.py
│       ├── __main__.py              # python -m 入口
│       ├── app.py                   # 主程序核心类
│       ├── cli.py                   # CLI 命令行入口
│       ├── gui.py                   # Web GUI (Gradio)
│       ├── desktop_gui.py           # 桌面 GUI (tkinter，支持拖拽)
│       ├── core/                    # 核心处理引擎
│       │   ├── format_corrector.py  # 格式矫正器
│       │   ├── format_exporter.py   # 多格式导出
│       │   ├── file_converter.py    # 文件格式转换
│       │   └── style_extractor.py   # 模板样式提取
│       ├── handlers/                # 文档组件处理器
│       │   ├── table_handler.py     # 表格处理
│       │   ├── header_footer_handler.py  # 页眉页脚
│       │   ├── image_handler.py     # 图片处理
│       │   ├── figure_table_handler.py   # 图表编号
│       │   └── toc_handler.py       # 目录处理
│       ├── parsers/                 # 文档解析与检测
│       │   ├── section_detector.py  # 章节检测
│       │   ├── requirement_parser.py # 需求文档解析
│       │   ├── reference_formatter.py # 参考文献格式化
│       │   ├── ref_auto_complete.py # 参考文献自动补全
│       │   ├── cross_reference.py   # 交叉引用
│       │   └── llm_parser.py        # LLM 智能解析
│       ├── quality/                 # 质量评估与规则
│       │   ├── quality_scorer.py    # 质量评分
│       │   ├── diff_reporter.py     # 差异对比报告
│       │   └── rule_engine.py       # 自定义规则引擎
│       ├── generators/              # 内容生成
│       │   └── cover_page_generator.py  # 封面生成
│       └── infra/                   # 基础设施
│           ├── logger.py            # 日志
│           ├── plugin_manager.py    # 插件管理
│           └── path_security.py     # 路径安全校验
├── config/
│   └── config.yaml                  # 配置文件
├── tests/                           # 测试
├── input/                           # 输入目录
├── output/                          # 输出目录
├── template/                        # 模板目录
├── pyproject.toml                   # 项目配置
└── requirements.txt                 # 依赖
```

## 联系我们

本项目为开源项目，如果您在使用过程中遇到任何问题或有任何建议，欢迎通过以下方式联系我们：

- **GitHub**: https://github.com/blankLeaving99/paper-format-corrector
- **问题反馈**: 请提交 Issue 到上述仓库，我们会第一时间处理

感谢您的使用与支持！

## 许可证

MIT
