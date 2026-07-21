<div align="center">

# 📝 论文格式自动矫正工具

**Paper Format Corrector v3.0**

基于模板和规则，一键矫正 Word 论文格式

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![CI](https://img.shields.io/badge/CI-Passing-brightgreen.svg)](https://github.com/blankLeaving99/paper-format-corrector/actions)

</div>

---

## 项目介绍

论文格式自动矫正工具是一款基于 Python 的学术论文格式处理工具，能够根据预设模板或自定义需求文档，自动矫正 Word 论文的字体、字号、行距、对齐、缩进、页边距等格式问题。

支持国际期刊格式（IEEE、Nature、Science、APA）和中国大学毕业论文格式，提供桌面 GUI、Web GUI 和 CLI 三种使用方式。

### 为什么需要这个工具？

- 毕业论文格式要求繁琐，手动调整耗时数小时
- 不同期刊/会议格式各异，反复修改容易出错
- 图表编号、参考文献格式容易遗漏或不统一
- 本工具可在 **30 秒内** 完成一篇论文的格式矫正

---

## 核心功能

| 功能 | 说明 |
|------|------|
| **格式预设** | 内置 38 种格式预设（IEEE、Nature、Science、APA、中国高校等） |
| **智能矫正** | 自动识别标题层级、正文、摘要、参考文献等，应用对应格式 |
| **需求文档驱动** | 从 `.docx`/`.txt`/`.md` 解析学校格式要求并自动应用 |
| **LLM 智能解析** | 使用 OpenAI/Anthropic/Ollama 理解复杂排版需求 |
| **质量评分** | 矫正后对文档格式规范性打分（0-100） |
| **差异对比** | 生成矫正前后的 HTML 对比报告 |
| **多格式导出** | 支持 PDF、HTML、Markdown、TXT、LaTeX 导出 |
| **BibTeX 解析** | 解析 .bib 文件，自动转换为项目参考文献格式 |
| **PDF 反向学习** | 从 PDF 提取格式规则，支持 OCR 降级 |
| **封面生成** | 根据元数据自动生成论文封面页 |
| **图表编号** | 自动编号图、表、公式，支持按章节编号 |
| **参考文献格式化** | GB/T 7714、IEEE、APA 等多种引用格式 |
| **页眉页脚** | 自动设置页眉、页码 |
| **目录生成** | 自动生成/更新目录 |
| **批量处理** | 一键处理整个目录的文档，支持异步任务队列 |
| **多语言字体** | 支持中文/日文/韩文东亚字体自动适配 |
| **双 GUI** | 桌面 GUI（原生窗口，支持拖拽）+ Web GUI（浏览器） |
| **Word 插件** | Office Add-in 插件，在 Word 内直接矫正格式 |
| **插件系统** | 自定义矫正规则，支持第三方插件 |

---

## 快速安装

### 方式一：使用 exe（推荐，无需 Python）

1. 下载 `论文格式矫正工具.exe`
2. 双击运行，按提示选择安装路径
3. 选择 GUI 模式即可使用

### 方式二：双击 run.py

直接双击 `run.py`，程序会自动管理虚拟环境和依赖安装，全程无需命令行。

### 方式三：pip 安装

```bash
git clone https://github.com/blankLeaving99/paper-format-corrector.git
cd paper-format-corrector

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# 安装核心依赖
pip install -r requirements.txt

# 安装可选功能
pip install "paper-format-corrector[all]"  # 全部功能
pip install "paper-format-corrector[ocr]"  # OCR 支持（扫描件 PDF）
pip install "paper-format-corrector[remote]"  # 远程服务（数据库+认证）
```

---

## 快速使用

### 三步矫正论文

```bash
# 第 1 步：放入论文
# 将 my_paper.docx 放入 input/ 目录

# 第 2 步：选择格式矫正
python -m paper_format_corrector --preset ieee -f input/my_paper.docx

# 第 3 步：查看结果
# 矫正后的文件保存在 output/ 目录
```

### 带质量评分和对比

```bash
python -m paper_format_corrector -f input/paper.docx --score --diff
```

### 启动 GUI

```bash
python -m paper_format_corrector --gui           # Web GUI（浏览器）
python -m paper_format_corrector --desktop-gui    # 桌面 GUI（原生窗口）
```

### 启动 API 服务

```bash
python -m paper_format_corrector.api.app
# API 文档：http://localhost:8000/docs
```

### 异步批量处理

```bash
python -m paper_format_corrector batch input/ -o output/ --async
# 提交到任务队列，通过 API 查询进度: GET /tasks/{task_id}
```

### LaTeX 导出

```bash
python -m paper_format_corrector -f input/paper.docx --export latex
# 或通过 API: POST /export/latex
```

---

## 格式预设

工具内置 **38 种** 格式预设，覆盖主流期刊、会议和高校：

| 预设 | 说明 | 适用场景 |
|------|------|----------|
| `ieee` | IEEE Transactions/会议 | 9pt 正文，Times New Roman |
| `nature` | Nature 期刊 | 10pt 正文，结构化摘要 |
| `science` | Science 期刊 | 10pt 正文，1.5 倍行距 |
| `apa` | APA 第 7 版 | 12pt 正文，双倍行距 |
| `chinese_thesis` | 中国大学毕业论文 | 宋体/黑体，GB/T 7714 |
| `tsinghua` | 清华大学 | 研究生学位论文 |
| `peking` | 北京大学 | 研究生学位论文 |
| `zhejiang` | 浙江大学 | 研究生学位论文 |
| `acm` | ACM 格式 | ACM 期刊/会议 |
| `springer` | Springer 格式 | Springer 期刊 |
| `elsevier` | Elsevier 格式 | Elsevier 期刊 |
| ... | 共 38 种 | 查看全部：`--list-presets` |

```bash
# 查看所有预设
python -m paper_format_corrector --list-presets
```

---

## 文档链接

| 文档 | 说明 |
|------|------|
| [用户使用手册](docs/user_guide.md) | 安装指南、快速开始、GUI/CLI 使用说明、FAQ |
| [模板开发指南](docs/template_guide.md) | YAML 模板结构、字段详解、学校模板提取方法 |
| [API 使用指南](docs/api_guide.md) | REST API 启动、调用示例、端点说明、错误码 |
| [贡献指南](CONTRIBUTING.md) | 项目结构、开发环境、代码规范、PR 流程 |
| [示例文件](examples/) | 示例模板、需求文档、矫正前后对比论文 |
| [变更日志](CHANGELOG.md) | 版本更新记录 |

---

## 项目结构

```
paper-format-corrector/
├── run.py                          # 启动器（自动管理虚拟环境）
├── build.py                        # 打包为 exe
├── pyproject.toml                  # 项目配置
├── config/config.yaml              # 默认配置
├── presets/                        # 38 种格式预设
├── src/paper_format_corrector/     # 主包
│   ├── app.py                      # 核心编排器
│   ├── cli.py                      # CLI 入口
│   ├── gui.py                      # Web GUI (Gradio)
│   ├── desktop_gui.py              # 桌面 GUI (tkinter)
│   ├── infrastructure/             # 基础设施层
│   │   ├── converters/             # 文件转换与格式化
│   │   ├── exporters/              # 多格式导出（PDF/HTML/LaTeX）
│   │   ├── handlers/               # 文档组件处理器
│   │   ├── parsers/                # 解析器（BibTeX/PDF/LLM）
│   │   ├── queue/                  # 任务队列与 Worker
│   │   └── adapters/               # 外部适配器
│   ├── application/                # 应用服务层
│   ├── api/                        # REST API (FastAPI)
│   ├── shared/                     # 共享工具（字体/错误消息）
│   └── core/                       # 兼容性 shim（已废弃）
├── interfaces/word_addin/          # Word Add-in 插件
├── tests/                          # 测试套件（569 tests）
├── docs/                           # 文档
├── examples/                       # 示例文件
└── template/                       # 默认模板
```

---

## 贡献者

感谢所有为本项目做出贡献的开发者！

### 核心开发者

| 开发者 | GitHub | 角色 |
|--------|--------|------|
| blankLeaving99 | [@blankLeaving99](https://github.com/blankLeaving99) | 项目发起人、核心架构师 |
| root165 (zhangwanjian) | [@root165](https://github.com/root165) | 协作者、贡献者 |
| xiaocai | [@xiaocai](https://github.com/xiaocai) | 协作者、贡献者 |

### 所有贡献者

<a href="https://github.com/blankLeaving99/paper-format-corrector/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=blankLeaving99/paper-format-corrector" />
</a>

---

## 许可证

本项目采用 [MIT 许可证](LICENSE) 开源。

---

## 联系方式

- **GitHub**: https://github.com/blankLeaving99/paper-format-corrector
- **问题反馈**: 请提交 [Issue](https://github.com/blankLeaving99/paper-format-corrector/issues)

感谢您的使用与支持！
