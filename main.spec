# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

spec_path = Path(globals().get('__file__', 'main.spec')).resolve()
workspace_root = spec_path.parent
app_root = workspace_root / 'enterprise_tools'
icon_candidates = [
    app_root / 'assets' / 'iconoavis.ico',
    app_root / 'assets' / 'iconoaavis.ico',
    app_root / 'assets' / 'app_icon.ico',
]
app_icon = next((path for path in icon_candidates if path.exists()), None)
qtawesome_datas = collect_data_files('qtawesome')

a = Analysis(
    [str(app_root / 'main.py')],
    pathex=[],
    binaries=[],
    datas=[(str(app_root / 'faqs'), 'faqs'), (str(app_root / 'assets'), 'assets')] + qtawesome_datas,
    hiddenimports=['PySide6.QtWidgets', 'PySide6.QtGui', 'PySide6.QtCore', 'qtawesome', 'psutil'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='main',
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
    icon=str(app_icon) if app_icon else None,
)
