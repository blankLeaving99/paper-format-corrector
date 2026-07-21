---
kind: build_system
name: Python 项目构建与打包体系
category: build_system
scope:
    - '**'
source_files:
    - pyproject.toml
    - build.py
    - 论文格式矫正工具.spec
    - .github/workflows/ci.yml
    - requirements.txt
    - run.py
---

本项目采用基于 setuptools + PyInstaller 的 Python 应用构建方案，提供源码安装、可选依赖分组以及 Windows 单文件 exe 打包三种分发形态。

## 构建系统与工具链
- 包管理：使用 pyproject.toml 声明式配置，后端为 setuptools.build_meta，要求 Python ≥3.9。
- 依赖管理：核心依赖集中在 requirements.txt，同时通过 [project.optional-dependencies] 按功能域拆分为 pdf、html、gui、drag-drop、all、dev 等可选组，支持 pip install paper-format-corrector[gui] 按需安装。
- 可执行入口：通过 [project.scripts] 注册 paper-fmt 和 paper-correct 两个 CLI 命令，指向 paper_format_corrector.cli:main。
- 代码质量：Ruff 作为 lint/format 工具（行宽 120、目标 py39），pytest 运行测试并生成覆盖率报告（排除 GUI 模块）。

## 打包与分发
- PyInstaller 单文件打包：根目录提供 build.py 脚本与论文格式矫正工具.spec 配置文件，将源码、config、template、presets 等资源以 --add-data 方式内嵌，输出名为“论文格式矫正工具.exe”的单文件可执行程序，启用 UPX 压缩且隐藏控制台窗口。
- 自启动器（run.py）：双击运行时自动检测是否处于 venv；若否，则引导用户选择含中文的安装路径，创建 .venv 虚拟环境并安装全部核心与可选依赖，随后用 os.execv 重启到 venv 中执行桌面或 Web GUI。该逻辑同时兼容直接运行与打包后运行两种场景。
- CI 流水线：.github/workflows/ci.yml 在 push/PR 到 main 时触发，矩阵覆盖 Python 3.9 与 3.12，依次执行 ruff 检查与 pytest 测试。

## 架构约定
- 源码位于 src/paper_format_corrector/，通过 [tool.setuptools.packages.find] where = ["src"] 发现。
- 版本由 pyproject.toml 中的 version = "3.0.0" 统一管理，CLI 与 GUI 均从同一来源读取。
- 可选依赖与 run.py 内置的 _DEPS / _OPTIONAL_DEPS 列表保持同步，确保打包产物与运行时依赖一致。

## 开发者规则
- 新增依赖应同时更新 pyproject.toml 对应 optional-dependency 组、requirements.txt 注释说明以及 run.py 的依赖清单，避免运行时缺失。
- 修改打包资源需同步调整 build.py 的 --add-data 参数与论文格式矫正工具.spec 的 datas 字段。
- 发布新版本时仅修改 pyproject.toml 的 version 字段，无需改动其他构建配置。