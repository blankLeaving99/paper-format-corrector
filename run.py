"""论文格式自动矫正工具 v3.0 - 启动器

双击运行即可使用。支持直接运行和打包为 exe 后运行。
"""

import sys
import os

# 获取项目根目录（支持 exe 打包后运行）
if getattr(sys, 'frozen', False):
    # 打包为 exe 后，根目录是 exe 所在目录
    ROOT_DIR = os.path.dirname(sys.executable)
else:
    # 直接运行 Python 脚本
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


def check_deps():
    """检查必要依赖是否已安装"""
    missing = []
    for mod, pkg in [("docx", "python-docx"), ("yaml", "pyyaml"), ("lxml", "lxml")]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    return missing


def install_deps(missing):
    """弹窗让用户选择安装依赖"""
    import tkinter as tk
    from tkinter import messagebox, filedialog
    import subprocess

    root = tk.Tk()
    root.withdraw()

    items = "\n".join(f"  - {p}" for p in missing)
    msg = f"以下依赖未安装：\n\n{items}\n\n是否安装？"
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

        # 安装依赖
        subprocess.run([pip_exe, "install", "--upgrade", "pip"], capture_output=True)
        subprocess.run([pip_exe, "install"] + missing, check=True)

        # 保存虚拟环境位置
        with open(os.path.join(ROOT_DIR, ".venv_location"), "w") as f:
            f.write(venv_dir)

        messagebox.showinfo("安装完成",
                            f"依赖已安装到：\n{venv_dir}\n\n"
                            f"请重新运行 run.py")
        return False  # 需要重新运行

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

    # 居中
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
        # 1. 检查必要依赖
        missing = check_deps()
        if missing:
            if not install_deps(missing):
                return

        # 2. 选择模式
        mode = choose_mode()
        if mode is None:
            return

        # 3. 启动对应 GUI
        if mode == "desktop":
            from paper_format_corrector.desktop_gui import main as run
        else:
            from paper_format_corrector.gui import main as run

        run()

    except KeyboardInterrupt:
        pass
    except Exception as e:
        show_error("运行错误", f"程序出错：\n\n{e}")


if __name__ == "__main__":
    main()
