import os
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('production_zero.data', includes=['*.json'])
datas += collect_data_files('production_zero', includes=[
    'assets/freight/*.svg', 'assets/freight/*.png', 'assets/machines/*.png',
    'assets/resources/*.png', 'assets/ui/*.png'])
datas += [(os.environ['INDUSTRIOVA_PERFORMANCE_BUILD_METADATA'], 'production_zero/data')]
a = Analysis(['src/production_zero/app/__main__.py'], pathex=['src'], binaries=[], datas=datas,
             hiddenimports=[], hookspath=[], hooksconfig={},
             runtime_hooks=['scripts/performance_test_runtime_hook.py', 'scripts/performance_test_smoke_hook.py'],
             excludes=['pytest', 'tests'], noarchive=False, optimize=0)
pyz = PYZ(a.pure)
blocked_dlls = {'icuuc.dll', 'icudt78.dll', 'icuin.dll'}
a.binaries = [item for item in a.binaries if item[0].lower() not in blocked_dlls]
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Industriova_Performance_Test',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=True, console=False,
          version='scripts/industriova_performance_version.txt', disable_windowed_traceback=False,
          argv_emulation=False, target_arch=None, codesign_identity=None, entitlements_file=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, upx_exclude=[],
               name='Industriova_Performance_Test')
