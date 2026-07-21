# 贡献指南

感谢你对论文格式自动矫正工具的贡献！本文档将帮助你快速上手开发。

---

## 目录

- [1. 项目结构说明](#1-项目结构说明)
- [2. 开发环境搭建](#2-开发环境搭建)
- [3. 代码风格规范](#3-代码风格规范)
- [4. PR 流程](#4-pr-流程)
- [5. 测试要求](#5-测试要求)

---

## 1. 项目结构说明

```
paper-format-corrector/
├── run.py                          # 启动器（双击运行，自动管理虚拟环境）
├── build.py                        # PyInstaller 打包脚本
├── pyproject.toml                  # 项目配置（构建、依赖、工具）
├── requirements.txt                # 依赖列表
├── config/
│   └── config.yaml                 # 默认配置文件
├── presets/                        # 格式预设（YAML）
│   ├── ieee.yaml                   # IEEE 期刊/会议格式
│   ├── nature.yaml                 # Nature 期刊格式
│   ├── chinese_thesis.yaml         # 中国大学毕业论文格式
│   ├── templates_index.yaml        # 预设索引
│   └── doc_templates/              # 文档模板（报告、合同等）
├── src/
│   └── paper_format_corrector/     # 主包（src 布局）
│       ├── __init__.py             # 版本号
│       ├── __main__.py             # python -m 入口
│       ├── app.py                  # 核心编排器（PaperFormatCorrector）
│       ├── cli.py                  # CLI 命令行入口
│       ├── gui.py                  # Web GUI（Gradio）
│       ├── desktop_gui.py          # 桌面 GUI（tkinter）
│       ├── core/                   # 核心处理引擎
│       │   ├── format_corrector.py # 格式矫正主引擎
│       │   ├── style_extractor.py  # 模板样式提取
│       │   ├── file_converter.py   # 文件格式转换
│       │   └── format_exporter.py  # 多格式导出
│       ├── parsers/                # 文档解析与检测
│       │   ├── section_detector.py # 段落类型检测
│       │   ├── requirement_parser.py # 需求文档解析
│       │   ├── llm_parser.py       # LLM 智能解析
│       │   ├── reference_formatter.py # 参考文献格式化
│       │   └── modules/            # 检测模块（标题、正文等）
│       ├── handlers/               # 文档组件处理器
│       │   ├── table_handler.py    # 表格格式化
│       │   ├── image_handler.py    # 图片处理
│       │   ├── header_footer_handler.py # 页眉页脚
│       │   └── toc_handler.py      # 目录生成
│       ├── quality/                # 质量评估
│       │   ├── quality_scorer.py   # 质量评分
│       │   ├── diff_reporter.py    # 差异对比
│       │   └── rule_engine.py      # 自定义规则引擎
│       ├── generators/             # 内容生成
│       │   └── cover_page_generator.py # 封面生成
│       ├── infra/                  # 基础设施
│       │   ├── preset_loader.py    # 预设加载
│       │   ├── template_repository.py # SQLite 模板库
│       │   ├── plugin_manager.py   # 插件管理
│       │   └── path_security.py    # 路径安全校验
│       ├── api/                    # REST API
│       │   ├── app.py              # FastAPI 服务
│       │   └── client.py           # Python 客户端
│       └── application/            # 应用服务层
│           └── services/           # 业务服务
├── tests/                          # 测试套件
│   ├── conftest.py                 # 共享 fixtures
│   ├── test_corrector.py           # 矫正器测试
│   ├── test_presets.py             # 预设测试
│   └── ...                         # 其他测试文件
├── template/
│   └── template.docx               # 默认模板文件
├── docs/                           # 文档
├── examples/                       # 示例文件
├── plugins/                        # 插件目录
└── static/                         # 静态资源（图标等）
```

### 核心模块职责

| 模块 | 职责 |
|------|------|
| `app.py` | 中央编排器，管理配置加载、预设/需求应用、文件处理 |
| `core/format_corrector.py` | 逐段落格式矫正引擎 |
| `parsers/section_detector.py` | 检测段落类型（标题、正文、摘要等） |
| `parsers/requirement_parser.py` | 解析自然语言需求文档为配置字典 |
| `handlers/table_handler.py` | 表格三线表格式化 |
| `quality/quality_scorer.py` | 多维度质量评分（0-100） |
| `infra/preset_loader.py` | 加载和验证 YAML 预设 |
| `infra/template_repository.py` | SQLite 模板库 CRUD |

---

## 2. 开发环境搭建

### 2.1 前置要求

- Python 3.9+
- Git
- 推荐使用 VS Code / PyCharm

### 2.2 克隆并设置

```bash
# 克隆仓库
git clone https://github.com/blankLeaving99/paper-format-corrector.git
cd paper-format-corrector

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 安装核心依赖
pip install -r requirements.txt

# 安装开发依赖
pip install "paper-format-corrector[dev]"

# 安装所有可选依赖（用于完整测试）
pip install "paper-format-corrector[all]"
```

### 2.3 验证安装

```bash
# 运行测试
pytest tests/ -v

# 代码检查
ruff check src/ tests/

# 确认 CLI 可用
python -m paper_format_corrector --help
```

### 2.4 IDE 配置

**VS Code 推荐扩展**：

- Python
- Ruff
- Pylance

**推荐设置**（`.vscode/settings.json`）：

```json
{
  "python.defaultInterpreterPath": ".venv/Scripts/python.exe",
  "python.analysis.typeCheckingMode": "basic",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true
  }
}
```

---

## 3. 代码风格规范

### 3.1 Linter：Ruff

项目使用 Ruff 进行代码检查和格式化。配置在 `pyproject.toml`：

```toml
[tool.ruff]
line-length = 120
target-version = "py39"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B"]
ignore = ["E501"]
```

### 3.2 运行检查

```bash
# 检查代码
ruff check src/ tests/

# 自动修复
ruff check --fix src/ tests/

# 格式化
ruff format src/ tests/
```

### 3.3 编码规范

- **Python 版本**：3.9+，使用 `from __future__ import annotations`
- **类型注解**：公共函数和方法必须添加类型注解
- **文档字符串**：公共 API 使用中文 docstring
- **导入顺序**：标准库 → 第三方库 → 本项目模块（Ruff 自动排序）
- **命名规范**：
  - 文件名：`snake_case.py`
  - 类名：`PascalCase`
  - 函数/变量：`snake_case`
  - 常量：`UPPER_SNAKE_CASE`
  - 私有方法：`_leading_underscore`

### 3.4 安全规范

- 永远使用 `yaml.safe_load()`，禁止 `yaml.load()`
- `subprocess.run()` 使用列表参数，禁止 `shell=True`
- 文件路径必须通过 `path_security.py` 校验
- 用户输入必须验证和清理

---

## 4. PR 流程

### 4.1 分支策略

```
main          ← 稳定发布版本
  └── dev     ← 开发集成分支
       └── feature/xxx   ← 功能分支
       └── fix/xxx       ← 修复分支
       └── docs/xxx      ← 文档分支
```

### 4.2 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Type 类型**：

| Type | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响功能） |
| `refactor` | 重构 |
| `test` | 测试相关 |
| `chore` | 构建/工具变更 |

**示例**：

```
feat(presets): add Tsinghua University thesis preset
fix(parser): handle empty abstract section
docs: update API guide with batch endpoint
test(corrector): add edge case for single-paragraph doc
```

### 4.3 PR 步骤

1. **从 `dev` 分支创建功能分支**

```bash
git checkout dev
git pull origin dev
git checkout -b feature/my-feature
```

2. **开发并提交**

```bash
# 开发...
git add .
git commit -m "feat(module): add new feature"
```

3. **推送并创建 PR**

```bash
git push origin feature/my-feature
```

在 GitHub 上创建 PR，目标分支为 `dev`。

4. **填写 PR 模板**

- **标题**：简洁描述变更内容
- **描述**：
  - 变更内容
  - 相关 Issue 编号
  - 测试情况
  - 截图（如涉及 UI）

5. **等待 CI 通过和 Code Review**

6. **合并后删除功能分支**

### 4.4 PR 检查清单

- [ ] 代码通过 `ruff check` 无错误
- [ ] 新增/修改代码有对应测试
- [ ] 所有测试通过
- [ ] 文档已更新（如需要）
- [ ] 无安全问题（无硬编码密钥、无路径遍历漏洞）
- [ ] 提交信息符合规范

---

## 5. 测试要求

### 5.1 测试框架

- **pytest** — 测试运行器
- **pytest-cov** — 覆盖率报告
- **conftest.py** — 共享 fixtures

### 5.2 运行测试

```bash
# 运行全部测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_corrector.py -v

# 运行特定测试
pytest tests/test_corrector.py::test_basic_correction -v

# 覆盖率报告
pytest tests/ --cov=src/paper_format_corrector --cov-report=html
```

### 5.3 测试文件结构

```
tests/
├── conftest.py                 # 共享 fixtures（config, template_path 等）
├── test_basic.py               # 基础导入测试
├── test_corrector.py           # 核心矫正功能
├── test_presets.py             # 预设加载和结构
├── test_requirement.py         # 需求文档解析
├── test_edge_cases.py          # 边界情况
├── test_image_table.py         # 图表处理
├── test_path_security.py       # 路径安全
├── test_thesis.py              # 毕业论文集成
└── ...
```

### 5.4 编写测试

**基本测试模板**：

```python
import pytest
from paper_format_corrector.app import PaperFormatCorrector


class TestMyFeature:
    """我的功能测试"""

    def test_basic_functionality(self, config, tmp_path):
        """测试基本功能"""
        # 准备
        input_file = tmp_path / "input.docx"
        # ... 创建测试文件

        # 执行
        corrector = PaperFormatCorrector()
        result = corrector.process_single(str(input_file))

        # 验证
        assert result is not None
        assert result["status"] == "success"

    def test_edge_case_empty(self, tmp_path):
        """测试空文件边界情况"""
        input_file = tmp_path / "empty.docx"
        # ... 创建空文件

        corrector = PaperFormatCorrector()
        result = corrector.process_single(str(input_file))
        # 验证不崩溃
```

### 5.5 测试覆盖要求

- **新功能**：必须有对应测试
- **Bug 修复**：必须有回归测试
- **边界情况**：空文件、单段落、超大文件等
- **安全相关**：路径校验、输入验证必须有测试

### 5.6 CI/CD

GitHub Actions 自动运行：

- **Python 版本**：3.9 和 3.12
- **检查项**：ruff lint + pytest
- **PR 必须通过所有检查才能合并**

---

## 附录：有用的命令

```bash
# 开发时常用命令
ruff check --fix src/ tests/          # 自动修复 lint 问题
ruff format src/ tests/               # 格式化代码
pytest tests/ -x -v                   # 遇到第一个失败就停止
pytest tests/test_presets.py -k "ieee" # 运行匹配的测试

# 查看项目信息
python -c "import paper_format_corrector; print(paper_format_corrector.__version__)"
python -m paper_format_corrector --list-presets
```

如有问题，欢迎提交 Issue 或联系维护者！
