# 用户使用手册

论文格式自动矫正工具 v3.0 — 完整使用指南

---

## 目录

- [1. 安装指南](#1-安装指南)
- [2. 快速开始](#2-快速开始)
- [3. Web GUI 使用说明](#3-web-gui-使用说明)
- [4. 桌面 GUI 使用说明](#4-桌面-gui-使用说明)
- [5. CLI 命令参考](#5-cli-命令参考)
- [6. 常见问题 FAQ](#6-常见问题-faq)

---

## 1. 安装指南

### 1.1 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10+、macOS 10.15+、Linux |
| Python | 3.9 及以上 |
| 内存 | 建议 4GB+（处理大文档时） |
| 磁盘空间 | 至少 500MB（含依赖） |

### 1.2 方式一：使用 exe（推荐，无需安装 Python）

1. 下载 `论文格式矫正工具.exe`
2. 双击运行
3. 首次运行会自动检测依赖，按提示选择安装路径
4. 选择「桌面 GUI」或「Web GUI」

### 1.3 方式二：双击 run.py

直接双击项目根目录下的 `run.py`，程序会自动：

1. 检测是否有已存在的虚拟环境（`.venv`），如有则自动切换
2. 检测依赖是否安装（包括可选依赖：gradio、tkinterdnd2、pdfplumber 等）
3. 如有缺失，弹窗提示并让你选择安装位置，安装完成后自动重启
4. 弹出模式选择窗口，选择桌面 GUI 或 Web GUI

全程无需手动激活虚拟环境或打开命令行。

### 1.4 方式三：pip 安装

```bash
# 克隆仓库
git clone https://github.com/blankLeaving99/paper-format-corrector.git
cd paper-format-corrector

# 创建虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

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

### 1.5 打包为 exe

```bash
python build.py
```

打包完成后，`dist/` 目录下的 exe 文件可以直接发给他人使用，无需安装 Python。

---

## 2. 快速开始

### 三步矫正论文

**第 1 步：准备文件**

将待矫正的论文放入 `input/` 目录：

```
input/
└── my_paper.docx
```

**第 2 步：运行矫正**

```bash
# 使用预设格式矫正
python -m paper_format_corrector --preset ieee -f input/my_paper.docx

# 或使用需求文档驱动
python -m paper_format_corrector -r my_requirements.txt -f input/my_paper.docx
```

**第 3 步：查看结果**

矫正后的文件保存在 `output/` 目录。添加 `--score` 和 `--diff` 可获取质量评分和对比报告：

```bash
python -m paper_format_corrector -f input/my_paper.docx --score --diff
```

---

## 3. Web GUI 使用说明

启动方式：

```bash
python -m paper_format_corrector --gui
# 或
python -m paper_format_corrector.gui
```

浏览器会自动打开，地址默认为 `http://127.0.0.1:7860`。

### Tab 1：论文矫正

**功能**：核心矫正功能，上传论文并选择格式进行矫正。

**操作步骤**：

1. **上传论文** — 拖拽或点击上传 `.docx` 文件
2. **选择格式预设** — 从下拉框选择预设（IEEE / Nature / Science / APA / 中国毕业论文 等）
3. **可选上传** — 模板文件（`.docx`）、需求文档（`.txt`/`.md`/`.docx`）、自定义配置（`.yaml`）
4. **选项** — 勾选「质量评分」获取分数，勾选「差异对比」生成对比报告
5. **导出格式** — 可同时导出 PDF / HTML / Markdown / TXT
6. **点击「开始矫正」**

**输出**：
- 矫正后的 `.docx` 文件下载
- 质量评分报告（0-100 分）
- HTML 差异对比报告（可下载）

### Tab 2：格式工作台

**功能**：高级格式调整，可精细控制每个元素的样式。

**操作步骤**：

1. **上传论文** — 选择要调整的论文
2. **选择模板** — 从内置模板库选择，或上传样本文档
3. **扫描元素** — 点击「扫描」分析文档中的标题、正文、表格、图片
4. **调整样式** — 修改正文、标题、表格、图片的字体/字号/间距等
5. **预览计划** — 查看将要进行的修改（dry-run）
6. **应用** — 执行修改

**特殊功能**：
- **学习样本** — 上传排版正确的样本文档，工具会学习其格式规则
- **低置信度段落** — 对未自动识别的段落进行手动覆盖

### Tab 3：模板库

**功能**：管理内置和个人模板。

**操作**：

- **浏览** — 按分类筛选（期刊/会议/毕业论文/出版社）
- **搜索** — 关键词搜索模板
- **详情** — 查看模板的完整格式配置
- **导入** — 导入 `.yaml` 或 `.json` 格式的模板文件
- **导出** — 将模板导出为 YAML/JSON
- **删除** — 删除个人模板（内置模板仅禁用）

### Tab 4：报告中心

**功能**：查看历史处理记录。

**操作**：

- 查看所有处理历史（ID、文件名、状态、分数、时间）
- 点击查看详情
- 删除历史记录

### Tab 5：批量处理

**功能**：一次处理多个论文文件。

**操作步骤**：

1. **上传文件** — 选择多个 `.docx` 文件
2. **选择模板** — 选择统一的格式预设
3. **点击「开始批量处理」**
4. **下载结果** — 下载包含所有矫正文件和汇总报告的 ZIP 压缩包

### Tab 6：封面生成

**功能**：根据论文信息自动生成封面页。

**填写字段**：

- 论文题目、作者、学院、专业、学号
- 指导教师、日期、学校名称
- 文档类型（本科/硕士/博士论文）

**操作**：填写信息 → 选择模板（标准/研究生）→ 点击「生成封面」→ 下载

### Tab 7：AI 文档生成

**功能**：用 LLM 从大纲描述生成文档内容。

**操作步骤**：

1. **配置 LLM** — 选择提供商（OpenAI/Anthropic/Ollama），填入 API Key 和模型名
2. **输入描述** — 描述你要生成的文档内容
3. **发送** — AI 会流式生成内容
4. **导出** — 将生成的内容导出为 `.docx`

### Tab 8：规则检查

**功能**：使用自定义 YAML 规则文件检查论文。

**操作**：

1. 上传论文文件
2. 上传 YAML 规则文件
3. 点击「检查」
4. 查看检查报告

### Tab 9：帮助

提供使用说明和联系方式的 Markdown 文档。

---

## 4. 桌面 GUI 使用说明

启动方式：

```bash
python -m paper_format_corrector --desktop-gui
```

桌面 GUI 使用 tkinter 原生窗口，支持文件拖拽（需安装 `tkinterdnd2`）。

### 主要功能

- **论文矫正** — 拖拽文件、选择预设、一键矫正
- **格式工作台** — 精细调整每个元素的样式
- **模板库** — 完整的模板管理（增删改查）
- **批量处理** — 选择多个文件批量矫正
- **封面生成** — 填写信息生成封面
- **规则检查** — 上传规则文件检查格式
- **历史记录** — 查看所有处理记录

### 拖拽支持

直接将 `.docx` 文件拖拽到输入框即可（需安装 `tkinterdnd2`）。

### 窗口要求

- 最小窗口：800 x 600
- 默认窗口：900 x 700

---

## 5. CLI 命令参考

### 5.1 子命令模式（推荐）

```bash
python -m paper_format_corrector <子命令> [选项]
```

| 子命令 | 说明 | 示例 |
|--------|------|------|
| `correct` | 矫正单个论文 | `correct -f paper.docx --preset ieee` |
| `scan` | 扫描文档结构 | `scan -f paper.docx` |
| `learn` | 从样本学习格式 | `learn -f sample.docx` |
| `batch` | 批量处理目录 | `batch -i input/ -o output/` |
| `report` | 查看报告 | `report --report-id 1` |
| `template list` | 列出模板 | `template list --category journal` |
| `template import` | 导入模板 | `template import my_template.yaml` |
| `template export` | 导出模板 | `template export ieee -o ieee.yaml` |
| `template info` | 查看模板详情 | `template info ieee` |
| `template delete` | 删除模板 | `template delete my_template` |

### 5.2 常用选项

| 选项 | 说明 | 示例 |
|------|------|------|
| `-f, --file` | 输入文件路径 | `-f paper.docx` |
| `-o, --output` | 输出文件路径 | `-o output/corrected.docx` |
| `-t, --template` | 模板文件路径 | `-t template.docx` |
| `--preset` | 格式预设名称 | `--preset ieee` |
| `-r, --requirement` | 需求文档路径 | `-r requirement.txt` |
| `--no-template` | 不使用模板 | `--no-template` |
| `--score` | 启用质量评分 | `--score` |
| `--diff` | 生成差异对比报告 | `--diff` |
| `--format` | 导出格式 | `--format pdf html md` |
| `--rules` | 自定义规则文件 | `--rules my_rules.yaml` |
| `-c, --config` | 配置文件路径 | `-c my_config.yaml` |
| `--log-level` | 日志级别 | `--log-level DEBUG` |

### 5.3 LLM 相关选项

| 选项 | 说明 |
|------|------|
| `--llm` | 启用 LLM 智能解析 |
| `--llm-provider` | 提供商：`openai` / `anthropic` / `ollama` |
| `--llm-key` | API Key |
| `--llm-model` | 模型名称 |
| `--llm-base-url` | 自定义端点 URL |
| `--offline-parser` | 使用离线规则解析器 |
| `--list-models` | 列出可用模型 |

### 5.4 封面生成选项

```bash
python -m paper_format_corrector --cover \
  title="论文题目" \
  author="张三" \
  college="计算机学院" \
  major="计算机科学与技术" \
  student_id="2021001" \
  advisor="李教授" \
  date="2025年6月" \
  university="示例大学" \
  type="本科毕业论文"
```

### 5.5 GUI 启动选项

```bash
python -m paper_format_corrector --gui           # Web GUI
python -m paper_format_corrector --desktop-gui    # 桌面 GUI
```

### 5.6 完整示例

```bash
# 矫正 + 评分 + 对比 + 导出 PDF
python -m paper_format_corrector -f paper.docx --preset ieee --score --diff --format pdf

# 批量处理 + LLM 解析
python -m paper_format_corrector batch -i input/ -o output/ -r requirement.txt --llm --llm-key sk-xxx

# 查看所有预设
python -m paper_format_corrector --list-presets
```

---

## 6. 常见问题 FAQ

### Q1: 支持哪些文件格式？

**输入**：`.docx`（推荐）、`.doc`、`.odt`、`.rtf`、`.pdf`、`.txt`、`.md`

非 `.docx` 格式会自动转换，其中 `.doc` 需要 LibreOffice 或 `docx2docx` 库。

### Q2: 矫正后文件内容会丢失吗？

不会。工具只修改格式（字体、字号、行距、对齐等），不会删除或修改文字内容。代码块和公式也会被自动保护。

### Q3: 如何使用自己的学校格式？

三种方式：

1. **需求文档** — 将学校格式要求写成 `.txt`/`.md`/`.docx` 文件，用 `-r` 参数指定
2. **预设 + 需求文档** — 先选一个最接近的预设，再用需求文档微调
3. **样本文档学习** — 在格式工作台中上传排版正确的样本文档，让工具学习其格式规则

### Q4: LLM 解析是什么意思？

工具可以使用大语言模型（如 GPT-4、Claude、Ollama 本地模型）来理解复杂的需求文档。对于自然语言描述的格式要求，LLM 解析比规则解析更准确。

```bash
python -m paper_format_corrector -r requirement.txt -f paper.docx --llm --llm-key sk-xxx
```

### Q5: 质量评分是怎么计算的？

工具会从多个维度评估文档格式的规范性（字体、字号、行距、对齐、缩进、页边距、标题层级等），给出 0-100 的综合分数。分数越高表示格式越规范。

### Q6: 差异对比报告是什么？

生成一个 HTML 文件，展示矫正前后的并排对比。可以清楚看到哪些地方被修改了。

### Q7: 批量处理的输出在哪里？

批量处理的结果默认保存在 `output/` 目录。使用 Web GUI 批量处理时，会下载一个 ZIP 压缩包，包含所有矫正文件和汇总报告。

### Q8: 如何创建自定义规则？

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
python -m paper_format_corrector -f paper.docx --rules my_rules.yaml
```

### Q9: 插件系统如何使用？

在 `plugins/` 目录下创建 Python 文件，继承 `Plugin` 基类：

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

### Q10: 模板库在哪里？

模板库使用本地 SQLite 数据库 `data/template_library.db`，不需要网络服务。内置 YAML 预设会在首次使用时自动写入模板库；个人模板只保存在本机。

### Q11: 如何导出矫正后的 PDF？

```bash
# 需要安装 pdf 可选依赖
pip install "paper-format-corrector[pdf]"

# 矫正并导出 PDF
python -m paper_format_corrector -f paper.docx --format pdf
```

### Q12: 遇到问题怎么办？

1. 查看日志：添加 `--log-level DEBUG` 获取详细日志
2. 检查依赖：运行 `python -c "from paper_format_corrector.infra.compat import check_dependencies; check_dependencies()"`
3. 提交 Issue：https://github.com/blankLeaving99/paper-format-corrector/issues
