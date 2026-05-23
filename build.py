"""打包脚本 - 将桌面 GUI 打包为 exe

用法：
    E:\Python\python_3_13_3\python.exe build.py

打包完成后，exe 文件在 dist/ 目录下。
"""

import subprocess
import sys
import os
import shutil

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    print("=" * 50)
    print("  论文格式矫正工具 - 打包为 exe")
    print("=" * 50)

    # 1. 检查 PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller 版本: {PyInstaller.__version__}")
    except ImportError:
        print("正在安装 PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    # 2. 检查必要依赖
    print("\n检查依赖...")
    required = ["docx", "yaml", "lxml"]
    missing = []
    for mod in required:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)

    if missing:
        print(f"缺少依赖: {missing}")
        print("请先安装: pip install python-docx pyyaml lxml")
        return

    # 3. 检查可选依赖
    optional_ok = []
    optional_missing = []
    for mod, name in [("tkinterdnd2", "拖拽支持"), ("gradio", "Web GUI")]:
        try:
            __import__(mod)
            optional_ok.append(name)
        except ImportError:
            optional_missing.append(name)

    if optional_ok:
        print(f"已安装可选功能: {', '.join(optional_ok)}")
    if optional_missing:
        print(f"未安装可选功能: {', '.join(optional_missing)}（不影响打包）")

    # 4. 清理旧的构建文件
    for d in ["build", "dist"]:
        path = os.path.join(ROOT_DIR, d)
        if os.path.exists(path):
            print(f"清理: {path}")
            shutil.rmtree(path)

    spec_file = os.path.join(ROOT_DIR, "paper_format_corrector.spec")
    if os.path.exists(spec_file):
        os.remove(spec_file)

    # 5. 创建入口脚本
    entry_script = os.path.join(ROOT_DIR, "_build_entry.py")
    with open(entry_script, "w", encoding="utf-8") as f:
        f.write('''"""打包入口"""
import sys
import os

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.join(BASE_DIR, "src"))

from paper_format_corrector.desktop_gui import main

if __name__ == "__main__":
    main()
''')

    # 6. 收集数据文件
    datas = []

    # config 目录
    config_dir = os.path.join(ROOT_DIR, "config")
    if os.path.exists(config_dir):
        datas.append((config_dir, "config"))

    # template 目录
    template_dir = os.path.join(ROOT_DIR, "template")
    if os.path.exists(template_dir):
        datas.append((template_dir, "template"))

    # src 目录（包含所有 Python 模块）
    src_dir = os.path.join(ROOT_DIR, "src")
    if os.path.exists(src_dir):
        datas.append((src_dir, "src"))

    # 7. 构建 PyInstaller 参数
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",              # 不显示控制台窗口
        "--name=论文格式矫正工具",   # exe 文件名
        "--icon=NONE",             # 可以替换为 .ico 图标文件
        "--add-data=config;config",
        "--add-data=template;template",
        "--add-data=src;src",
        "--hidden-import=docx",
        "--hidden-import=yaml",
        "--hidden-import=lxml",
        "--hidden-import=tkinter",
        "--hidden-import=tkinterdnd2",
        "--hidden-import=gradio",
        entry_script,
    ]

    print(f"\n开始打包...")
    print(f"命令: {' '.join(cmd)}")
    print()

    # 8. 执行打包
    result = subprocess.run(cmd, cwd=ROOT_DIR)

    # 9. 清理临时文件
    if os.path.exists(entry_script):
        os.remove(entry_script)

    if result.returncode == 0:
        dist_dir = os.path.join(ROOT_DIR, "dist")
        exe_path = os.path.join(dist_dir, "论文格式矫正工具.exe")

        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"\n{'=' * 50}")
            print(f"  打包成功！")
            print(f"  输出: {exe_path}")
            print(f"  大小: {size_mb:.1f} MB")
            print(f"{'=' * 50}")
            print(f"\n使用方法:")
            print(f"  1. 将 dist/论文格式矫正工具.exe 发给朋友")
            print(f"  2. 朋友双击即可运行，无需安装 Python")
            print(f"  3. 首次运行会自动检测并提示安装依赖")
        else:
            print(f"\n打包完成，但未找到 exe 文件，请检查 dist/ 目录")
    else:
        print(f"\n打包失败，请检查错误信息")


if __name__ == "__main__":
    main()
