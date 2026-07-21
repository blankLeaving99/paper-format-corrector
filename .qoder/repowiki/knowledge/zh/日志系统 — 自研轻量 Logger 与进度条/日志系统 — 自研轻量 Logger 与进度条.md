---
kind: logging_system
name: 日志系统 — 自研轻量 Logger 与进度条
category: logging_system
scope:
    - '**'
source_files:
    - src/paper_format_corrector/infra/logger.py
    - src/paper_format_corrector/shared/utils/logger.py
    - src/paper_format_corrector/app.py
    - src/paper_format_corrector/application/services/batch_service.py
    - run.py
---

## 1. 系统概述
本项目未使用 Python 标准库 `logging` 作为主日志框架，而是实现了一个自研的轻量级 `Logger` 类（同时提供 `ProgressBar`），用于控制台彩色输出、可选文件落盘以及线程安全写入。GUI/CLI 顶层异常捕获处会回退到 `logging.getLogger(__name__).exception(...)` 记录未处理异常。

## 2. 核心组件
- `src/paper_format_corrector/infra/logger.py`：定义 `Logger` 与 `ProgressBar`，是应用层主要依赖的实现。
- `src/paper_format_corrector/shared/utils/logger.py`：与 infra 版本完全相同的重复实现，当前未被业务代码引用，属于冗余副本。
- `run.py` 顶层 `except Exception:` 分支通过 `import logging; logging.getLogger(__name__).exception(...)` 兜底记录未处理异常。

## 3. 架构与约定
- **级别**：仅支持 `DEBUG / INFO / WARNING / ERROR` 四级，内部以整数映射控制过滤。
- **输出目标**：默认打印到 stdout；若构造时传入 `log_file`，则追加写入该文件，并在进程退出时自动关闭（`atexit` + `__del__`）。
- **并发安全**：文件写入使用 `threading.Lock` 保护，避免多线程/多进程竞争。
- **颜色**：当 `color=True` 且 `sys.stdout.isatty()` 为真时启用 ANSI 颜色（DEBUG=青色、INFO=绿色、WARNING=黄色、ERROR=红色）。
- **格式**：每行形如 `[HH:MM:SS] [LEVEL] message`，无结构化字段（JSON 等）。
- **进度条**：`ProgressBar` 在单行内用 `\r` 刷新显示百分比与 ETA，完成时换行。

## 4. 使用方式与调用点
- 主程序入口 `PaperFormatCorrector.__init__` 创建 `self.logger = Logger(level=log_level)`，后续通过 `self.logger.info/warning/error/debug` 输出运行信息。
- 批量处理流程中通过 `ProgressBar(len(tasks), desc="Processing")` 展示整体进度。
- `application/services/batch_service.py` 同样直接实例化 `Logger` 并记录批处理日志。
- GUI 模块 (`desktop_gui.py`, `gui.py`) 直接使用 `logging.getLogger(__name__).exception(...)` 记录界面交互异常。

## 5. 开发者规范
- 业务逻辑优先通过注入的 `Logger` 实例记录日志，不要直接 `print`。
- 需要持久化日志时在构造 `Logger(log_file=...)` 指定路径，父目录会自动创建。
- 不要在子进程中共享同一个 `Logger` 实例（`ProcessPoolExecutor` 场景下每个进程应自行创建）。
- 如需结构化日志或统一收集，建议迁移至标准 `logging` 或第三方库（当前实现不支持 handler 扩展）。