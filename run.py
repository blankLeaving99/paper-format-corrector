"""论文格式自动矫正工具 v3.0 - 启动器

双击运行即可使用。支持直接运行和打包为 exe 后运行。

安装流程：
  1. 首次运行 → 弹窗选择安装路径（必须含中文）
  2. 在选定路径下创建 .venv 虚拟环境并安装依赖
  3. 安装路径记录到 setup_config.json
  4. 后续运行自动读取配置，跳过安装直接启动
"""

import os
import re
import sys

# 获取项目根目录（支持 exe 打包后运行）
if getattr(sys, 'frozen', False):
    ROOT_DIR = os.path.dirname(sys.executable)
else:
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

# ─── 配置文件 ───────────────────────────────────────────────

CONFIG_FILE = os.path.join(ROOT_DIR, "setup_config.json")


def _has_chinese(text):
    """检查字符串中是否包含中文字符"""
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def _load_config():
    """加载安装配置"""
    import json
    if not os.path.isfile(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_config(install_dir):
    """保存安装配置"""
    import json
    config = {
        "install_dir": install_dir,
        "venv_dir": os.path.join(install_dir, ".venv"),
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _validate_install_path(path):
    """验证安装路径：必须存在、含中文、可写"""
    if not path or not os.path.isdir(path):
        return False, "选择的路径不存在"
    if not _has_chinese(path):
        return False, "安装路径必须包含中文字符，请重新选择"
    try:
        test_file = os.path.join(path, ".write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
    except Exception:
        return False, "安装路径不可写，请选择其他目录"
    return True, ""


# ─── 错误提示 ───────────────────────────────────────────────

def show_error(title, msg):
    """弹窗显示错误"""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, msg)
    except Exception:
        print(f"\n{'=' * 50}")
        print(f"错误: {title}")
        print(msg)
        print(f"{'=' * 50}")
        input("\n按回车键退出...")


# ─── 虚拟环境检测 ──────────────────────────────────────────

def _is_running_in_venv():
    """判断当前是否已在虚拟环境中运行"""
    return hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )


def _find_venv_python_at(venv_dir):
    """在指定目录中查找 venv 的 Python 可执行文件，验证可用性后返回路径"""
    import subprocess
    candidate = os.path.join(venv_dir, "Scripts", "python.exe")
    if not os.path.isfile(candidate):
        return None
    try:
        result = subprocess.run(
            [candidate, "--version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and "Python" in result.stdout:
            return candidate
    except Exception:
        pass
    return None


def _check_deps_at(python_path):
    """在指定 Python 环境中检查依赖，返回缺失列表"""
    import subprocess

    check_script = (
        "missing = []\n"
        "for mod, name, ver in [\n"
        "    ('docx', 'python-docx', '1.1.0'),\n"
        "    ('yaml', 'pyyaml', '6.0'),\n"
        "    ('lxml', 'lxml', '5.0'),\n"
        "    ('PIL', 'Pillow', '9.0'),\n"
        "]:\n"
        "    try:\n"
        "        __import__(mod)\n"
        "    except ImportError:\n"
        "        missing.append(f'{name}>={ver}')\n"
        "print('|'.join(missing))"
    )
    try:
        result = subprocess.run(
            [python_path, "-c", check_script],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("|")
        return []
    except Exception:
        return ["检查失败"]


# ─── 环境查找与安装 ────────────────────────────────────────

def _find_or_create_env():
    """查找已有环境或引导用户创建新环境，返回可用的 venv Python 路径"""
    config = _load_config()

    # 1. 有配置文件 → 检查该路径下的 venv 是否可用
    if config and config.get("venv_dir"):
        venv_dir = config["venv_dir"]
        python_path = _find_venv_python_at(venv_dir)
        if python_path:
            missing = _check_deps_at(python_path)
            if not missing:
                return python_path
            # venv 存在但依赖不全 → 提示重装
            _offer_reinstall(venv_dir, config.get("install_dir", ROOT_DIR))
            return python_path  # os.execv 已重启
        # venv 不存在了 → 用保存的 install_dir 重建
        install_dir = config.get("install_dir", ROOT_DIR)
        return _do_install(install_dir)

    # 2. 无配置 → 检查默认位置的 venv（兼容旧版 .venv_location）
    old_venv = os.path.join(ROOT_DIR, ".venv")
    python_path = _find_venv_python_at(old_venv)
    if python_path:
        missing = _check_deps_at(python_path)
        if not missing:
            _save_config(ROOT_DIR)
            return python_path

    # 3. 无任何可用环境 → 引导安装
    return _first_time_install()


def _first_time_install():
    """首次安装：弹窗让用户选择含中文的安装路径"""
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.withdraw()

    optional_names = [f"{pip}>={min_ver}" for _, pip, min_ver, _, _ in _OPTIONAL_DEPS]

    msg = (
        "欢迎使用论文格式矫正工具！\n\n"
        "首次运行需要安装 Python 虚拟环境和依赖包。\n"
        "请点击[是]选择安装目录（路径必须包含中文字符）。\n\n"
        "将安装以下可选依赖：\n"
        + "\n".join(f"  - {p}" for p in optional_names)
    )
    if not messagebox.askyesno("环境配置", msg):
        show_error("提示", "需要安装依赖才能使用，程序即将退出。")
        sys.exit(0)

    while True:
        install_dir = filedialog.askdirectory(
            title="选择安装目录（路径必须包含中文字符）",
            initialdir=ROOT_DIR,
        )
        if not install_dir:
            show_error("提示", "未选择目录，程序即将退出。")
            sys.exit(0)

        ok, err = _validate_install_path(install_dir)
        if ok:
            break
        messagebox.showerror("路径无效", err)

    root.destroy()
    return _do_install(install_dir)


def _offer_reinstall(venv_dir, install_dir):
    """依赖不完整时提示重装"""
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()

    msg = (
        "检测到虚拟环境存在但依赖包不完整。\n"
        "是否重新安装所有依赖？"
    )
    if messagebox.askyesno("依赖不完整", msg):
        root.destroy()
        _do_install(install_dir)
    else:
        root.destroy()


def _do_install(install_dir):
    """在指定目录创建 venv 并安装依赖，完成后重启程序"""
    import subprocess
    import tkinter as tk
    from tkinter import messagebox

    venv_dir = os.path.join(install_dir, ".venv")

    root = tk.Tk()
    root.withdraw()

    try:
        # 创建虚拟环境（已存在则跳过）
        if not os.path.isdir(venv_dir):
            subprocess.run(
                [sys.executable, "-m", "venv", venv_dir],
                check=True,
            )

        pip_exe = os.path.join(venv_dir, "Scripts", "pip.exe")
        venv_python = os.path.join(venv_dir, "Scripts", "python.exe")

        # 收集所有依赖
        all_pkgs = (
            [f"{pip}>={min_ver}" for _, pip, min_ver, _, req in _DEPS if req]
            + [f"{pip}>={min_ver}" for _, pip, min_ver, _, req in _OPTIONAL_DEPS if not req]
        )

        # 安装依赖
        subprocess.run(
            [pip_exe, "install", "--upgrade", "pip"],
            capture_output=True,
        )
        subprocess.run(
            [pip_exe, "install"] + all_pkgs,
            check=True,
        )

        # 保存配置
        _save_config(install_dir)

        # 用 venv 的 Python 重启当前脚本
        run_script = os.path.abspath(__file__)
        os.execv(venv_python, [venv_python, run_script])

    except Exception as e:
        messagebox.showerror("安装失败", f"安装失败：\n{e}")
        sys.exit(1)


# ─── 依赖列表 ──────────────────────────────────────────────

_DEPS = [
    ("docx", "python-docx", "1.1.0", 2, True),
    ("yaml", "pyyaml", "6.0", 7, True),
    ("lxml", "lxml", "5.0", 7, True),
    ("PIL", "Pillow", "9.0", 11, True),
]

_OPTIONAL_DEPS = [
    ("gradio", "gradio", "4.0.0", None, False),
    ("tkinterdnd2", "tkinterdnd2", "0.4.0", None, False),
    ("docx2pdf", "docx2pdf", "0.1.8", None, False),
    ("mammoth", "mammoth", "1.6.0", None, False),
    ("pdfplumber", "pdfplumber", "0.10.0", None, False),
]


# ─── GUI 模式选择 ──────────────────────────────────────────

def choose_mode():
    """弹窗选择 GUI 模式"""
    import tkinter as tk

    root = tk.Tk()
    root.title("论文格式矫正工具 v3.0")
    root.geometry("400x250")
    root.resizable(False, False)

    root.update_idletasks()
    x = (root.winfo_screenwidth() - 400) // 2
    y = (root.winfo_screenheight() - 250) // 2
    root.geometry(f"400x250+{x}+{y}")

    result = {"mode": None}

    def pick(m):
        result["mode"] = m
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", lambda: pick(None))

    tk.Label(root, text="论文格式自动矫正工具 v3.0",
             font=("Microsoft YaHei", 15, "bold")).pack(pady=(25, 5))
    tk.Label(root, text="请选择启动模式：",
             font=("Microsoft YaHei", 10)).pack(pady=(0, 15))

    btn_kw = {"font": ("Microsoft YaHei", 10), "width": 30, "height": 2}
    tk.Button(root, text="桌面 GUI（推荐，原生窗口）",
              command=lambda: pick("desktop"), **btn_kw).pack(pady=5)
    tk.Button(root, text="Web GUI（浏览器打开）",
              command=lambda: pick("web"), **btn_kw).pack(pady=5)

    root.mainloop()
    return result["mode"]


# ─── 主入口 ────────────────────────────────────────────────

def main():
    try:
        # 1. 如果当前不在 venv 中，查找或创建可用环境（会 os.execv 重启）
        if not _is_running_in_venv():
            venv_python = _find_or_create_env()
            if venv_python and os.path.isfile(venv_python):
                os.execv(venv_python, [venv_python, os.path.abspath(__file__)] + sys.argv[1:])

        # 2. 如果传入了命令行参数，直接委托给 CLI
        if len(sys.argv) > 1:
            from paper_format_corrector.interfaces.cli.main import main as cli_main
            cli_main()
            return

        # 3. 已在 venv 中，二次确认依赖完整性
        try:
            from importlib.metadata import PackageNotFoundError, version
            missing = []
            for import_name, pip_name, min_ver, _, required in _DEPS:
                if not required:
                    continue
                try:
                    __import__(import_name)
                except ImportError:
                    missing.append(f"{pip_name}>={min_ver}")
                    continue
                try:
                    version(pip_name)
                except PackageNotFoundError:
                    missing.append(f"{pip_name}>={min_ver}")
            if missing:
                show_error(
                    "依赖缺失",
                    "以下依赖未安装：\n"
                    + "\n".join(f"  - {p}" for p in missing)
                    + "\n\n请删除 .venv 文件夹后重新运行程序。"
                )
                return
        except Exception:
            pass

        # 3. 选择 GUI 模式
        mode = choose_mode()
        if mode is None:
            return

        # 4. 启动对应 GUI
        if mode == "desktop":
            from paper_format_corrector.interfaces.desktop.app import main as run
        else:
            from paper_format_corrector.interfaces.web.app import main as run

        run()

    except KeyboardInterrupt:
        pass
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Unhandled error")
        show_error("运行错误", "程序出错，请检查输入文件是否正确。")


if __name__ == "__main__":
    main()
