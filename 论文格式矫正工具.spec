# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['E:\\Code\\TestALLCode\\paper-format-corrector\\_build_entry.py'],
    pathex=[],
    binaries=[],
    datas=[('src', 'src'), ('config', 'config'), ('template', 'template'), ('run.py', '.'), ('requirements.txt', '.')],
    hiddenimports=['docx', 'yaml', 'lxml', 'tkinter', 'tkinterdnd2'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['.venv', '__pycache__'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='论文格式矫正工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['static\\tubiao02.ico'],
)
