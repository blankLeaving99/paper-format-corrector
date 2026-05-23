"""日志系统

支持：
- 多级别日志 (DEBUG, INFO, WARNING, ERROR)
- 文件输出
- 控制台彩色输出
- 进度条显示
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime


class Logger:
    """日志管理器"""

    LEVELS = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}

    def __init__(self, level="INFO", log_file=None, color=True):
        self.level = self.LEVELS.get(level.upper(), 1)
        self.log_file = log_file
        self.color = color and sys.stdout.isatty()
        self._file_handle = None

        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            self._file_handle = open(log_file, "a", encoding="utf-8")

    def debug(self, msg):
        if self.level <= 0:
            self._log("DEBUG", msg, "\033[36m")  # cyan

    def info(self, msg):
        if self.level <= 1:
            self._log("INFO", msg, "\033[32m")  # green

    def warning(self, msg):
        if self.level <= 2:
            self._log("WARNING", msg, "\033[33m")  # yellow

    def error(self, msg):
        if self.level <= 3:
            self._log("ERROR", msg, "\033[31m")  # red

    def _log(self, level, msg, color_code):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] [{level:7}] {msg}"

        if self.color:
            print(f"{color_code}{line}\033[0m")
        else:
            print(line)

        if self._file_handle:
            self._file_handle.write(line + "\n")
            self._file_handle.flush()

    def close(self):
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None

    def __del__(self):
        self.close()


class ProgressBar:
    """进度条"""

    def __init__(self, total, desc="Processing", width=40):
        self.total = total
        self.desc = desc
        self.width = width
        self.current = 0
        self.start_time = time.time()

    def update(self, n=1):
        self.current += n
        self._display()

    def _display(self):
        if self.total == 0:
            return

        pct = self.current / self.total
        filled = int(self.width * pct)
        bar = "#" * filled + "-" * (self.width - filled)
        elapsed = time.time() - self.start_time

        if self.current > 0:
            eta = elapsed / self.current * (self.total - self.current)
            eta_str = f"{int(eta)}s"
        else:
            eta_str = "--"

        line = f"\r{self.desc}: |{bar}| {self.current}/{self.total} ({pct*100:.0f}%) ETA: {eta_str}"
        sys.stdout.write(line)
        sys.stdout.flush()

        if self.current >= self.total:
            print()

    def finish(self):
        self.current = self.total
        self._display()
