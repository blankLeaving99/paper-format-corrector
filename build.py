"""打包脚本 - 将项目打包为 exe

用法：
    python build.py

打包内容：仅源码 + 配置 + 模板，不包含虚拟环境。
朋友电脑上运行 exe 后会自动检测依赖并提示安装。
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

    # 2. 清理旧的构建文件
    for d in ["build", "dist"]:
        path = os.path.join(ROOT_DIR, d)
        if os.path.exists(path):
            print(f"清理: {path}")
            shutil.rmtree(path)

    spec_file = os.path.join(ROOT_DIR, "paper_format_corrector.spec")
    if os.path.exists(spec_file):
        os.remove(spec_file)

    # 3. 创建打包专用入口脚本（不包含虚拟环境）
    entry_script = os.path.join(ROOT_DIR, "_build_entry.py")
    with open(entry_script, "w", encoding="utf-8") as f:
        f.write('''"""打包入口 - 仅用于 PyInstaller"""
import sys
import os

# 获取 exe 所在目录
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 切换工作目录
os.chdir(BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "src"))

# 导入并运行启动器（包含依赖检测和 GUI 选择）
from run import main

if __name__ == "__main__":
    main()
''')

    # 4. 构建 PyInstaller 参数
    # 只打包必要的数据文件，不打包 .venv
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",                         # 打包为单个 exe 文件
        "--windowed",                        # 不显示控制台窗口
        "--name=论文格式矫正工具",             # exe 文件名
        "--icon=static/tubiao02.ico",          # exe 图标
        # 数据文件：只打包 src、config、template
        "--add-data=src;src",
        "--add-data=config;config",
        "--add-data=template;template",
        "--add-data=run.py;.",               # 打包启动器
        "--add-data=requirements.txt;.",     # 打包依赖列表
        # 排除虚拟环境和缓存
        "--exclude-module=.venv",
        "--exclude-module=__pycache__",
        # 隐藏导入
        "--hidden-import=docx",
        "--hidden-import=yaml",
        "--hidden-import=lxml",
        "--hidden-import=tkinter",
        "--hidden-import=tkinterdnd2",
        entry_script,
    ]

    print(f"\n开始打包...")
    print(f"注意：不包含虚拟环境和依赖\n")

    # 5. 执行打包
    result = subprocess.run(cmd, cwd=ROOT_DIR)

    # 6. 清理临时文件
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
            print(f"  1. 将 dist/论文格式矫正工具.exe 发给他人")
            print(f"  2. 您双击即可运行")
            print(f"  3. 首次运行会自动检测依赖并提示安装")
            print(f"  4. 您可以选择自己的安装路径")
        else:
            print(f"\n打包完成，但未找到 exe 文件，请检查 dist/ 目录")
    else:
        print(f"\n打包失败，请检查错误信息")


if __name__ == "__main__":
    main()
