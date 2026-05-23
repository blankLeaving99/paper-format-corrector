"""论文格式自动矫正工具 v3.0 - 启动器

双击运行即可使用。支持直接运行和打包为 exe 后运行。
"""

import sys
import os

# 获取项目根目录（支持 exe 打包后运行）
if getattr(sys, 'frozen', False):
    ROOT_DIR = os.path.dirname(sys.executable)
else:
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))


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


def _find_venv_python():
    """查找已有的虚拟环境 Python 路径"""
    import subprocess
    for name in (".venv", ".venv\\.venv"):
        candidate = os.path.join(ROOT_DIR, name, "Scripts", "python.exe")
        if os.path.isfile(candidate):
            try:
                result = subprocess.run(
                    [candidate, "--version"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and "Python" in result.stdout:
                    return candidate
            except Exception:
                continue
    return None


def _is_running_in_venv():
    """判断当前是否已在虚拟环境中运行"""
    return hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )


def _check_deps_fast():
    """快速检查所有必需依赖是否已安装"""
    from importlib.metadata import version, PackageNotFoundError
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
            installed = version(pip_name)
        except PackageNotFoundError:
            missing.append(f"{pip_name}>={min_ver}")
    return missing


# 全局依赖列表（与 compat.py 保持一致，但不强依赖 compat 能 import）
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


def install_deps():
    """弹窗让用户选择安装依赖，安装完成后自动重启"""
    import tkinter as tk
    from tkinter import messagebox, filedialog
    import subprocess

    root = tk.Tk()
    root.withdraw()

    missing_required = _check_deps_fast()
    optional_names = [f"{pip}>={min_ver}" for _, pip, min_ver, _, _ in _OPTIONAL_DEPS]

    items = "\n".join(f"  - {p}" for p in missing_required)
    opt_items = "\n".join(f"  - {p}" for p in optional_names)
    msg = (
        f"以下必需依赖未安装：\n{items}\n\n"
        f"以下可选依赖也将一并安装：\n{opt_items}\n\n"
        f"是否安装？"
    )
    if not messagebox.askyesno("依赖检测", msg):
        show_error("提示", "缺少必要依赖，无法启动。")
        return False

    install_dir = filedialog.askdirectory(
        title="选择安装目录（将在该目录创建 .venv 虚拟环境）",
        initialdir=ROOT_DIR,
    )
    if not install_dir:
        install_dir = ROOT_DIR

    venv_dir = os.path.join(install_dir, ".venv")

    try:
        # 创建虚拟环境
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
        pip_exe = os.path.join(venv_dir, "Scripts", "pip.exe")
        venv_python = os.path.join(venv_dir, "Scripts", "python.exe")

        # 安装所有依赖
        all_pkgs = missing_required + optional_names
        subprocess.run([pip_exe, "install", "--upgrade", "pip"], capture_output=True)
        subprocess.run([pip_exe, "install"] + all_pkgs, check=True)

        # 保存虚拟环境位置
        with open(os.path.join(ROOT_DIR, ".venv_location"), "w") as f:
            f.write(venv_dir)

        # 自动重启：用 venv 的 Python 重新执行 run.py
        run_script = os.path.abspath(__file__)
        os.execv(venv_python, [venv_python, run_script])

    except Exception as e:
        messagebox.showerror("安装失败", f"安装失败：\n{e}")
        return False


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


def main():
    try:
        # 1. 如果不在 venv 中，尝试切换到已有的 venv
        if not _is_running_in_venv():
            venv_python = _find_venv_python()
            if venv_python and os.path.isfile(venv_python):
                os.execv(venv_python, [venv_python, os.path.abspath(__file__)])

        # 2. 检查必需依赖
        missing = _check_deps_fast()
        if missing:
            if not install_deps():
                return

        # 3. 选择模式
        mode = choose_mode()
        if mode is None:
            return

        # 4. 启动对应 GUI
        if mode == "desktop":
            from paper_format_corrector.desktop_gui import main as run
        else:
            from paper_format_corrector.gui import main as run

        run()

    except KeyboardInterrupt:
        pass
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Unhandled error")
        show_error("运行错误", "程序出错，请检查输入文件是否正确。")


if __name__ == "__main__":
    main()
