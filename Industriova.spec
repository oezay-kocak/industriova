# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files


datas = collect_data_files("production_zero.data", includes=["*.json"])
datas += collect_data_files("production_zero", includes=["assets/freight/*.svg", "assets/freight/*.png"])
datas += collect_data_files("production_zero", includes=["assets/machines/*.png"])
datas += collect_data_files("production_zero", includes=["assets/resources/*.png"])
datas += collect_data_files("production_zero", includes=["assets/ui/*.png"])

a = Analysis(
    ["src/production_zero/app/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["scripts/playtest_runtime_hook.py"],
    excludes=["pytest", "tests"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# PySide6 6.11.1 on Windows uses the system ICU exports. In this workspace,
# PyInstaller can otherwise pick up incompatible Poppler ICU DLLs from PATH.
blocked_dlls = {"icuuc.dll", "icudt78.dll", "icuin.dll"}
a.binaries = [item for item in a.binaries if item[0].lower() not in blocked_dlls]

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Industriova",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    version="scripts/industriova_version.txt",
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Industriova",
)
