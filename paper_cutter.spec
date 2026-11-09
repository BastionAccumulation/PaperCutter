# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

windows = Path(os.environ['SystemRoot'])
os.environ['PATH'] = os.pathsep.join(str(path) for path in (
    Path(sys.executable).parent,
    Path(sys.base_prefix),
    windows / 'System32',
    windows,
))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app_icon.ico', '.'),
        ('assets/controls', 'assets/controls'),
    ],
    hiddenimports=[
        'PySide6.support.deprecated',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='切题辅助应用',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico',
)
