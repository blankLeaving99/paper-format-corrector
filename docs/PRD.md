# 论文格式智能矫正系统 — 项目需求文档 (PRD)

## 1. 项目概述

### 1.1 项目名称

Paper Format Corrector（论文格式自动矫正工具）

### 1.2 背景

学术论文撰写中，排版规范（引用格式、标题层级、字体字号、图表标注、页边距等）耗费大量精力且极易出错。不同期刊/院校的格式要求差异大，手动调整效率低、一致性差。

### 1.3 目标

开发一款独立桌面应用，通过自动扫描文档、识别格式偏差并一键修复，确保论文符合特定学术出版规范。

### 1.4 核心价值

- 用户无需了解复杂排版规范，工具自动完成格式矫正
- 支持国际期刊（IEEE、Nature、Science、APA）和中国大学毕业论文格式
- 支持自然语言/表格/文档形式的格式需求描述，自动解析并应用
- 提供质量评分和对比报告，让用户直观了解矫正效果

---

## 2. 用户角色

| 角色 | 需求 |
|------|------|
| 本科生/研究生 | 快速完成毕业论文排版，符合学校格式要求 |
| 科研人员 | 投稿前快速适配目标期刊格式规范 |
| 学术编辑 | 批量校验稿件格式规范性 |
| 普通用户 | 日常文档格式统一化处理 |

---

## 3. 功能需求

### 3.1 核心矫正模块

#### 3.1.1 文档结构扫描

- 自动识别标题层级（章/节/小节），支持中英文模式：
  - 中文："第一章"、"1.1"、"1.1.1"
  - 英文："I. INTRODUCTION"、"1 Introduction"、"1.1 Background"
- 自动识别摘要、关键词、参考文献、致谢、附录等结构段落
- 自动识别图标题、表标题、公式编号
- 自动检测文档语言（中/英/日/韩），匹配对应字体方案

#### 3.1.2 格式矫正

- 字体矫正：中文字体（宋体/黑体/楷体）、英文字体（Times New Roman）、标题字体
- 字号矫正：支持中文字号（二号、小四等）到 pt 值的自动映射
- 行距矫正：支持倍数行距、固定值行距、最小值行距
- 对齐矫正：居中、左对齐、两端对齐
- 首行缩进：按字符数设置（如 2 字符缩进）
- 页边距矫正：上下左右边距精确设置（cm）
- 页眉页脚：自动设置页眉文本、页码、奇偶页差异
- 目录生成：自动插入/更新目录

#### 3.1.3 代码块与公式保护

- 自动识别代码段落（等宽字体、缩进代码、Code 样式），保留原始格式不矫正
- 自动识别公式内容（Cambria Math 字体、数学 Unicode），保留原始格式不矫正
- 公式编号行仍按规则处理（右对齐、字体统一）
- 可配置：是否强制统一代码字体、公式是否居中

#### 3.1.4 图表处理

- 图表自动编号：支持按章节编号（图 1-1）或顺序编号（图 1）
- 图标题位置：图标题在图下方
- 表标题位置：表标题在表上方
- 图片自动居中 + 尺寸调整
- 表格格式统一（表头加粗、边框样式）

#### 3.1.5 参考文献格式化

- 支持格式标准：GB/T 7714、IEEE、Nature、Science、APA
- 正文引用编号格式化（上标/方括号/作者-年份）
- 参考文献列表自动排序和格式化
- 引用完整性检查（检测孤立引用和缺失引用）

### 3.2 格式预设系统

内置 5 种格式预设，一键切换：

| 预设 | 说明 | 正文字号 | 正文字体 |
|------|------|----------|----------|
| `ieee` | IEEE Transactions/会议论文 | 9pt | Times New Roman |
| `nature` | Nature 期刊 | 10pt | Times New Roman |
| `science` | Science 期刊 | 10pt | Times New Roman |
| `apa` | APA 第 7 版 | 12pt | Times New Roman |
| `chinese_thesis` | 中国大学毕业论文 | 小四 (12pt) | 宋体 |

预设以 YAML 文件存储在 `presets/` 目录，用户可自定义扩展。

### 3.3 需求文档驱动

用户可以用自然语言描述格式要求，工具自动解析并应用：

- 支持格式：`.txt` / `.md` / `.docx` / `.pdf`
- 自然语言解析：如"一级标题用黑体，二号字，居中，加粗"
- 表格解析：如"一级标题 | 黑体 | 二号 | 居中 | 加粗"
- LLM 智能解析：接入 OpenAI / Anthropic / Ollama，理解复杂排版需求
- 需求文档中可指定模板文件路径
- 配置优先级：需求文档 > 预设 > config.yaml 默认值

### 3.4 多格式导入

| 格式 | 说明 | 依赖 |
|------|------|------|
| .docx | Word 文档（推荐） | 内置支持 |
| .doc | 旧版 Word | LibreOffice 或 docx2docx |
| .odt | OpenDocument | LibreOffice |
| .rtf | Rich Text | LibreOffice |
| .pdf | PDF 文档 | pdfplumber / PyMuPDF / PyPDF2 |
| .txt | 纯文本 | 内置支持 |
| .md | Markdown | 内置支持 |

非 .docx 格式自动转换为 .docx 后处理。

### 3.5 导出功能

- PDF 导出（依赖 docx2pdf）
- HTML 导出（依赖 mammoth）
- Markdown / TXT 导出
- 矫正前后差异对比报告（HTML 格式）

### 3.6 质量评分

矫正后对文档格式规范性打分（0-100 分），按维度评分：
- 字体规范性
- 标题层级正确性
- 正文格式一致性
- 图表编号规范性
- 参考文献格式正确性

### 3.7 封面生成

根据用户填写的元数据（论文题目、作者、学院、专业等）自动生成标准封面页。

### 3.8 自定义规则检查

用户可编写 YAML 格式的规则文件，检查论文是否符合自定义要求：
- 参考文献数量上限
- 正文字号要求
- 图表编号格式
- 自定义正则匹配规则

---

## 4. 用户界面需求

### 4.1 启动器（run.py）

- 双击运行，自动检测并切换到已有虚拟环境
- 自动安装全部依赖（必需 + 可选），安装完成后自动重启
- 弹窗选择启动模式：桌面 GUI 或 Web GUI

### 4.2 桌面 GUI（tkinter）

- 原生窗口，支持文件拖拽（依赖 tkinterdnd2）
- 四个标签页：论文矫正、封面生成、规则检查、使用说明
- 文件选择区：论文文件、模板文件、格式要求文档、自定义配置
- 选项区：质量评分、对比报告、导出格式选择
- 操作按钮：开始矫正、批量矫正、打开结果目录
- 处理中禁用按钮防重复提交
- 批量处理显示进度

### 4.3 Web GUI（Gradio）

- 浏览器打开，绑定 127.0.0.1
- 文件大小限制 50MB
- 四个标签页：论文矫正、封面生成、规则检查、使用说明
- 格式预设下拉框选择
- 模板文件上传入口

### 4.4 CLI（命令行）

```bash
python -m paper_format_corrector -f paper.docx --score --diff
python -m paper_format_corrector --preset ieee -f paper.docx
python -m paper_format_corrector -r requirement.txt -f paper.docx
python -m paper_format_corrector --no-template -f paper.docx
python -m paper_format_corrector --gui
python -m paper_format_corrector --desktop-gui
```

---

## 5. 非功能需求

### 5.1 性能

- 单份论文（50,000 字以内）处理时间不超过 30 秒
- 批量处理支持进度显示

### 5.2 安全性

- YAML 使用 `safe_load()`，无反序列化风险
- 子进程调用使用列表参数，无命令注入风险
- 路径安全校验（输入/输出路径白名单、路径穿越检测）
- LLM 解析器域名白名单 + HTTPS 强制
- 临时文件退出时自动清理
- 错误信息脱敏，不泄露内部路径

### 5.3 可靠性

- 模板文件不存在时 fallback 到空白模板，不崩溃
- 可选依赖缺失时只提示功能不可用，不阻塞主流程
- 异常处理完整，GUI 不会因单次错误冻结

### 5.4 可扩展性

- 插件系统：继承 `Plugin` 基类即可扩展功能
- 格式预设：新增 YAML 文件即可添加新格式标准
- 自定义规则：YAML 格式规则文件，无需改代码

### 5.5 可移植性

- 支持 Windows / macOS / Linux
- 支持打包为 exe（PyInstaller），无需安装 Python
- Python 3.9+ 兼容

---

## 6. 技术架构

### 6.1 技术栈

- 语言：Python 3.9+
- 文档处理：python-docx、lxml
- 配置：PyYAML
- 图像处理：Pillow
- 桌面 GUI：tkinter + tkinterdnd2
- Web GUI：Gradio
- LLM 集成：urllib（内置 HTTP 客户端）
- 测试：pytest
- 代码检查：ruff
- 打包：PyInstaller

### 6.2 模块架构

```
run.py (启动器)
  ├── cli.py (CLI 入口)
  ├── gui.py (Web GUI)
  ├── desktop_gui.py (桌面 GUI)
  └── app.py (PaperFormatCorrector 主类)
        ├── core/
        │     ├── format_corrector.py (格式矫正器)
        │     ├── format_exporter.py (多格式导出)
        │     ├── file_converter.py (文件格式转换)
        │     └── style_extractor.py (模板样式提取)
        ├── parsers/
        │     ├── section_detector.py (章节/代码/公式检测)
        │     ├── requirement_parser.py (需求文档解析)
        │     ├── reference_formatter.py (参考文献格式化)
        │     └── llm_parser.py (LLM 智能解析)
        ├── handlers/
        │     ├── table_handler.py (表格处理)
        │     ├── image_handler.py (图片处理)
        │     ├── header_footer_handler.py (页眉页脚)
        │     └── toc_handler.py (目录处理)
        ├── quality/
        │     ├── quality_scorer.py (质量评分)
        │     ├── diff_reporter.py (差异对比)
        │     └── rule_engine.py (自定义规则引擎)
        ├── generators/
        │     └── cover_page_generator.py (封面生成)
        └── infra/
              ├── logger.py (日志)
              ├── plugin_manager.py (插件管理)
              ├── preset_loader.py (格式预设加载)
              ├── path_security.py (路径安全校验)
              └── compat.py (依赖兼容性检查)
```

### 6.3 处理管线

```
输入文档
  → 文件格式转换（非 .docx 转 .docx）
  → 加载模板样式
  → 检测文档语言
  → 应用页面设置（页边距）
  → 逐段落矫正：
      ├── 检测段落类型（章节/代码/公式/正文/图表标题等）
      ├── 代码段落 → 保留原始格式
      ├── 公式内容 → 保留原始格式
      ├── 标题 → 应用标题样式
      ├── 正文 → 应用正文字体/行距/缩进
      └── 图表标题 → 处理编号和格式
  → 表格格式矫正
  → 图片居中处理
  → 参考文献格式化
  → 目录生成
  → 页眉页脚设置
  → 公式编号处理
  → 保存输出文档
```

### 6.4 配置优先级

```
需求文档（-r 参数）> 格式预设（--preset）> config.yaml 默认值
```

合并方式：深度递归字典合并（`app.py:_merge_config()`）

---

## 7. 项目路线图

### 已完成（v3.0）

- [x] 核心矫正引擎（字体/字号/行距/缩进/页边距）
- [x] 章节自动检测（中英文标题模式）
- [x] 格式预设系统（IEEE/Nature/Science/APA/毕业论文）
- [x] 需求文档驱动（自然语言/表格/docx 解析）
- [x] LLM 智能解析（OpenAI/Anthropic/Ollama）
- [x] 多格式导入（.doc/.odt/.rtf/.pdf/.txt/.md）
- [x] 桌面 GUI + Web GUI
- [x] 启动器自动化（venv 自动管理）
- [x] 模板上传 + 模板兜底
- [x] 质量评分 + 差异对比
- [x] 参考文献格式化（GB/T 7714、IEEE 等）
- [x] 代码块和公式格式保护
- [x] 安全加固（路径校验、SSRF 防护、异常脱敏）
- [x] 自定义规则引擎
- [x] 封面生成
- [x] 批量处理

### 计划中（v4.0）

- [ ] Word 插件（Add-in）版本
- [ ] LaTeX 格式支持
- [ ] 参考文献完整性检查（孤立引用、缺失引用检测）
- [ ] 引用格式自动识别（上标/方括号/作者-年份）
- [ ] 正文引用与参考文献列表一致性校验
- [ ] 修改撤销（Undo）机制
- [ ] 文档格式预览（所见即所得）
- [ ] 更多格式预设（Chicago、MLA、Harvard）
- [ ] 云端模板库

---

## 8. 测试策略

### 8.1 测试范围

| 测试类型 | 覆盖内容 |
|----------|----------|
| 单元测试 | 各模块独立功能（解析器、检测器、评分器等） |
| 集成测试 | 完整矫正流程（输入 → 矫正 → 输出） |
| 边界测试 | 空文档、纯标题文档、单段落文档、混合语言文档 |
| 安全测试 | 路径穿越、配置注入、异常输入处理 |
| 回归测试 | 确保新功能不破坏已有矫正逻辑 |

### 8.2 测试命令

```bash
# 运行全部测试
.venv\Scripts\python.exe -m pytest tests/ -v

# 运行特定测试
.venv\Scripts\python.exe -m pytest tests/test_code_formula.py -v
.venv\Scripts\python.exe -m pytest tests/test_corrector.py -v
```

---

## 9. 部署与分发

### 9.1 源码运行

```bash
git clone <repo>
cd paper-format-corrector
python run.py  # 自动安装依赖、选择 GUI
```

### 9.2 打包为 exe

```bash
python build.py
# 输出：dist/论文格式矫正工具.exe
```

exe 包含：源码 + 配置 + 模板 + 预设，不含虚拟环境。首次运行自动检测依赖并提示安装。

### 9.3 目录结构

```
paper-format-corrector/
├── run.py                    # 启动器
├── build.py                  # 打包脚本
├── CLAUDE.md                 # 项目指引
├── src/paper_format_corrector/  # 源码
├── config/config.yaml        # 默认配置
├── presets/                   # 格式预设
├── template/template.docx    # 默认模板
├── tests/                    # 测试套件
├── input/                    # 输入目录
└── output/                   # 输出目录
```

---

## 10. 约束与限制

- 当前仅支持 .docx 格式的矫正，其他格式需先转换
- 复杂排版（多栏、嵌套表格、OLE 对象）可能无法完全解析
- LLM 解析需要网络连接和 API Key
- PDF 导出依赖 LibreOffice 或 docx2pdf
- 代码/公式的检测基于字体和字符特征，可能有误判
