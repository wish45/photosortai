# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for PhotoSorterAI."""

from PyInstaller.utils.hooks import get_module_file_contents
import sys

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include InsightFace models
        ('~/.insightface', 'insightface'),
    ],
    hiddenimports=[
        'insightface',
        'insightface.app',
        'onnxruntime',
        'cv2',
        'sklearn',
        'umap',
        'hdbscan',
        'PIL',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PhotoSorterAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

app = BUNDLE(
    exe,
    name='PhotoSorterAI.app',
    icon=None,
    bundle_identifier='com.photosortai.app',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': 'True',
        'CFBundleDevelopmentRegion': 'en',
        'CFBundleShortVersionString': '1.0.0',
    },
)
