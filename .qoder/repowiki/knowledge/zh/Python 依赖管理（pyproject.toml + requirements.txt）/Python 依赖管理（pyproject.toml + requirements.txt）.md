---
kind: dependency_management
name: Python 依赖管理（pyproject.toml + requirements.txt）
category: dependency_management
scope:
    - '**'
source_files:
    - pyproject.toml
    - requirements.txt
---

本项目采用 Python 生态的标准依赖管理模式，以 pyproject.toml 为权威声明源，辅以 requirements.txt 提供兼容安装方式，未使用 lockfile、私有仓库或 vendoring。

1. 使用的系统与工具
- 构建后端：setuptools.build_meta（要求 setuptools>=68.0, wheel）
- 包名与版本：paper-format-corrector==3.0.0，要求 Python >=3.9
- 依赖声明位置：pyproject.toml 的 [project.dependencies] 与 [project.optional-dependencies]
- 辅助清单：根目录 requirements.txt 仅复述核心依赖，用于传统 pip install -r 场景
- 无 lockfile：未发现 uv.lock、poetry.lock、Pipfile.lock 等锁定文件
- 无 vendoring：未发现 vendor/ 目录或第三方源码归档（cankao/python-docx 仅为参考文档，不参与构建）

2. 关键文件
- pyproject.toml：项目元数据、运行时依赖、可选依赖组、脚本入口、pytest/ruff/coverage 配置
- requirements.txt：精简版核心依赖清单（与 pyproject 中 core deps 一致）
- src/paper_format_corrector.egg-info/requires.txt：由 setuptools 生成，反映已安装时的依赖快照

3. 架构与约定
- 核心依赖（必须）：python-docx>=1.1.0,<2.0、pyyaml>=6.0,<7.0、lxml>=5.0,<7.0、Pillow>=9.0
- 可选依赖通过 extras 分组，按功能域切分：pdf（docx2pdf）、html（mammoth）、pdf-import（pdfplumber）、doc-convert（docx2docx）、gui（gradio）、drag-drop（tkinterdnd2）、sync（httpx）、dev（pytest、pytest-cov、ruff、httpx）、all（上述所有可选依赖并集）
- 可执行入口通过 [project.scripts] 注册两个命令：paper-fmt 与 paper-correct，均指向 paper_format_corrector.cli:main
- 包发现策略：[tool.setuptools.packages.find] where = ["src"]，遵循 src-layout

4. 开发者应遵循的规则
- 新增运行时依赖时，优先在 pyproject.toml 的 [project.dependencies] 中声明；若为可选能力，放入对应 extras 组
- 版本约束使用 >=X.Y,<Z.0 的宽松范围，避免过紧导致升级困难
- 如需锁定精确版本，应在 CI 或本地开发流程中自行引入 lockfile（当前仓库未内置）
- 不要修改 requirements.txt 中的核心依赖——它只是 pyproject.toml 的镜像副本，应以 pyproject 为准
- 可选依赖组命名应与功能语义对齐，保持 all 始终等于各子组并集
- 新增 CLI 命令需在 [project.scripts] 中注册，确保 pip install 后可直接调用