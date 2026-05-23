# 论文格式自动矫正工具 v3.0

基于模板和规则自动矫正 Word 论文格式的工具。支持国际期刊格式（IEEE、Nature、Science、APA）和中国大学毕业论文格式，提供桌面 GUI 和 Web GUI 两种界面。

## 功能特性

- **格式预设** — 内置 IEEE / Nature / Science / APA / 中国毕业论文 5 种格式预设，一键切换
- **格式自动矫正** — 字体、字号、行距、对齐、缩进、页边距等
- **标题层级识别** — 自动检测章/节/小节，支持中英文标题模式（"第一章"、"I. INTRODUCTION"、"1 Introduction" 等）
- **多语言支持** — 中文/英文/日文/韩文，自动匹配字体
- **多格式导入** — 支持 .docx / .doc / .odt / .rtf / .pdf / .txt / .md，自动转换
- **需求文档驱动** — 从 .docx / .txt / .md / .pdf 解析格式要求并自动应用
- **LLM 智能解析** — 用 OpenAI / Anthropic / Ollama 理解复杂排版需求
- **质量评分** — 矫正后对文档格式规范性打分（0-100）
- **差异对比** — 生成矫正前后的 HTML 对比报告
- **多格式导出** — 支持 PDF、HTML、Markdown、TXT
- **封面生成** — 根据元数据自动生成论文封面
- **图表编号修正** — 自动编号图、表、公式，支持按章节编号
- **参考文献格式化** — GB/T 7714、IEEE、Nature、Science、APA 等多种格式
- **页眉页脚** — 自动设置页眉、页码
- **目录生成** — 自动生成/更新目录
- **双 GUI 界面** — 桌面 GUI（原生窗口，支持拖拽）+ Web GUI（浏览器）
- **批量处理** — 一键处理整个目录的文档
- **插件系统** — 自定义矫正规则，支持第三方插件

## 快速开始

### 方式一：使用 exe（推荐，无需安装 Python）

1. 下载 `论文格式矫正工具.exe`
2. 双击运行
3. 首次运行会自动检测依赖，按提示选择安装路径
4. 选择桌面 GUI 或 Web GUI

### 方式二：双击 run.py

直接双击项目根目录下的 `run.py`，程序会自动：
1. 检测是否有已存在的虚拟环境（`.venv`），如有则自动切换过去
2. 检测依赖是否安装（包括可选依赖：gradio、tkinterdnd2、pdfplumber 等）
3. 如有缺失，弹窗提示并让你选择安装位置，安装完成后自动重启
4. 弹出模式选择窗口，选择桌面 GUI 或 Web GUI

全程无需手动激活虚拟环境或打开命令行。

### 方式三：命令行

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

双击 `run.py`，程序会自动：
- 创建虚拟环境（`.venv`）
- 安装所有必需和可选依赖
- 安装完成后自动重启，无需手动操作

所有依赖安装到你选择的目录下的虚拟环境中，不污染系统 Python。

### 手动安装

```bash
git clone https://github.com/blankLeaving99/paper-format-corrector.git
cd paper-format-corrector

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装核心依赖
pip install -r requirements.txt

# 安装可选功能（按需选择）
pip install "paper-format-corrector[gui]"        # Web GUI (Gradio)
pip install "paper-format-corrector[drag-drop]"   # 桌面 GUI 拖拽支持
pip install "paper-format-corrector[pdf]"          # PDF 导出
pip install "paper-format-corrector[html]"         # HTML 导出
pip install "paper-format-corrector[pdf-import]"   # PDF 文件导入

# 或一次性安装所有可选依赖
pip install "paper-format-corrector[all]"

# 开发依赖（测试 + 代码检查）
pip install "paper-format-corrector[dev]"
```

### 打包为 exe

```bash
python build.py
```

打包完成后，`dist/` 目录下的 exe 文件可以直接发给他人使用，无需安装 Python。

## 格式预设

工具内置 5 种国际/国内论文格式预设，使用 `--preset` 参数一键切换：

| 预设 | 说明 | 适用场景 |
|------|------|----------|
| `ieee` | IEEE Transactions/会议论文格式 | 9pt 正文，Times New Roman，Roman numeral 章节标题 |
| `nature` | Nature 期刊格式 | 10pt 正文，结构化摘要，上标引用编号 |
| `science` | Science 期刊格式 | 10pt 正文，1.5 倍行距，编号引用 |
| `apa` | APA 第 7 版格式 | 12pt 正文，双倍行距，5 级标题，作者-年份引用 |
| `chinese_thesis` | 中国大学毕业论文格式 | 宋体/黑体，GB/T 7714 参考文献，1.5 倍行距 |

```bash
# 列出所有可用预设
python -m paper_format_corrector --list-presets

# 使用 IEEE 格式矫正论文
python -m paper_format_corrector --preset ieee -f paper.docx

# 使用 Nature 格式矫正
python -m paper_format_corrector --preset nature -f paper.docx

# 使用 APA 格式矫正
python -m paper_format_corrector --preset apa -f paper.docx

# 中国毕业论文矫正
python -m paper_format_corrector --preset chinese_thesis -f paper.docx

# 预设 + 需求文档（需求文档会覆盖预设中的部分配置）
python -m paper_format_corrector --preset ieee -r my_requirements.txt -f paper.docx
```

在 Web GUI 中，格式预设以「格式预设」下拉框的形式出现在论文矫正页面顶部。

## 使用说明

### 命令行用法

```bash
# 批量处理 input/ 目录
python -m paper_format_corrector

# 处理单个文件
python -m paper_format_corrector -f input/paper.docx -o output/formatted.docx

# 使用格式预设
python -m paper_format_corrector --preset ieee -f paper.docx

# 需求文档驱动（需求文档中可指定模板路径）
python -m paper_format_corrector -r requirement.txt -f input/paper.docx

# 不使用模板，直接用配置规则矫正
python -m paper_format_corrector --no-template -f paper.docx

# 质量评分 + 差异对比
python -m paper_format_corrector -f input/paper.docx --score --diff

# LLM 智能解析
python -m paper_format_corrector -r requirement.txt -f paper.docx --llm --llm-key sk-xxx

# 导出多格式
python -m paper_format_corrector -f paper.docx --format pdf html md

# 生成封面
python -m paper_format_corrector --cover title="论文题目" author="张三" college="学院" major="专业"

# 自定义规则检查
python -m paper_format_corrector -f paper.docx --rules my_rules.yaml

# 查看模板信息
python -m paper_format_corrector --extract

# 启动 GUI
python -m paper_format_corrector --gui           # Web GUI（浏览器）
python -m paper_format_corrector --desktop-gui    # 桌面 GUI（原生窗口）
```

### 桌面 GUI 功能

- **格式预设选择** — 下拉框选择 IEEE / Nature / Science / APA / 毕业论文
- **文件拖拽** — 直接拖拽文件到输入框（需安装 tkinterdnd2）
- **批量处理** — 点击"批量矫正"按钮选择多个文件
- **论文矫正** — 上传论文、选择选项、一键矫正
- **封面生成** — 填写论文信息，自动生成封面
- **规则检查** — 上传论文和规则文件，检查格式

### 目录结构准备

将论文文件放入 `input/`，在 `template/` 放置模板 `.docx` 文件：

```
input/
├── paper1.docx
├── paper2.docx
template/
├── template.docx
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
| `format_rules.references` | 参考文献格式 |
| `format_rules.figures/tables` | 图表编号格式 |
| `format_rules.header_footer` | 页眉页脚、页码 |
| `format_rules.toc` | 目录 |
| `auto_detect` | 章节、摘要、关键词等正则模式 |

使用 `--preset` 时，预设配置会覆盖 `config.yaml` 中的对应字段。使用 `-r` 需求文档时，解析出的配置会进一步覆盖预设配置。优先级：**需求文档 > 预设 > config.yaml 默认值**。

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
python -m paper_format_corrector -f input/paper.docx --rules my_rules.yaml
```

## 插件系统

工具支持自定义插件扩展功能。在 `plugins/` 目录下创建插件文件，继承 `Plugin` 基类即可：

```python
from paper_format_corrector.infra.plugin_manager import Plugin

class MyPlugin(Plugin):
    name = "my_plugin"
    description = "自定义插件"
    priority = 100

    def process(self, doc, context):
        # 处理逻辑
        return context

    def get_report(self):
        return {"status": "done"}
```

详见 `plugins/example_word_count_plugin.py` 示例。

## 测试

```bash
# 运行全部测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_presets.py -v       # 格式预设测试
pytest tests/test_corrector.py -v     # 矫正器测试
pytest tests/test_edge_cases.py -v    # 边界情况测试
pytest tests/test_requirement.py -v   # 需求文档解析测试
pytest tests/test_thesis.py -v        # 毕业论文集成测试
```

## 项目结构

```
paper-format-corrector/
├── run.py                              # 启动器（双击运行，自动管理虚拟环境）
├── build.py                            # 打包为 exe 的脚本
├── CLAUDE.md                           # Claude Code 项目指引
├── .claude/
│   ├── tasks.md                        # 任务分解计划
│   └── settings.local.json             # 本地配置
├── presets/                            # 格式预设文件
│   ├── ieee.yaml                       # IEEE 期刊/会议格式
│   ├── nature.yaml                     # Nature 期刊格式
│   ├── science.yaml                    # Science 期刊格式
│   ├── apa.yaml                        # APA 第 7 版格式
│   └── chinese_thesis.yaml             # 中国大学毕业论文格式
├── src/
│   └── paper_format_corrector/
│       ├── __init__.py
│       ├── __main__.py                 # python -m 入口
│       ├── app.py                      # 主程序核心类
│       ├── cli.py                      # CLI 命令行入口
│       ├── gui.py                      # Web GUI (Gradio)
│       ├── desktop_gui.py              # 桌面 GUI (tkinter)
│       ├── core/                       # 核心处理引擎
│       ├── handlers/                   # 文档组件处理器
│       ├── parsers/                    # 文档解析与检测
│       ├── quality/                    # 质量评估与规则
│       ├── generators/                 # 内容生成
│       └── infra/                      # 基础设施（日志、预设、路径安全）
├── config/
│   └── config.yaml                     # 默认配置文件
├── template/
│   └── template.docx                   # 模板文件
├── tests/                              # 测试套件（93 个测试）
│   ├── conftest.py                     # 共享测试 fixtures
│   ├── test_basic.py                   # 基础导入测试
│   ├── test_corrector.py              # 矫正器功能测试
│   ├── test_edge_cases.py             # 边界情况测试
│   ├── test_presets.py                # 格式预设测试
│   ├── test_requirement.py            # 需求文档解析测试
│   ├── test_startup_and_template.py   # 启动流程 + 安全边界测试
│   └── test_thesis.py                 # 毕业论文集成测试
├── .github/
│   └── workflows/
│       └── ci.yml                      # GitHub Actions CI 配置
├── pyproject.toml                      # 项目配置（含 ruff、pytest）
├── requirements.txt                    # 依赖列表
├── CHANGELOG.md                        # 版本变更记录
└── README.md                           # 本文件
```

## 联系我们

本项目为开源项目，如果您在使用过程中遇到任何问题或有任何建议，欢迎通过以下方式联系我们：

- **GitHub**: https://github.com/blankLeaving99/paper-format-corrector
- **问题反馈**: 请提交 Issue 到上述仓库，我们会第一时间处理

感谢您的使用与支持！

## 许可证

MIT
