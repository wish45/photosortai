# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for PhotoSorterAI — Windows build."""

import os
import sys
from pathlib import Path

block_cipher = None

# InsightFace 모델 경로 (Windows)
insightface_models = os.path.join(Path.home(), '.insightface')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # InsightFace 모델 번들
        (insightface_models, 'insightface'),
        # 아이콘
        ('assets/icon.ico', 'assets'),
    ],
    hiddenimports=[
        'insightface',
        'insightface.app',
        'insightface.app.face_analysis',
        'insightface.model_zoo',
        'insightface.utils',
        'onnxruntime',
        'cv2',
        'sklearn',
        'sklearn.neighbors',
        'sklearn.utils._typedefs',
        'sklearn.utils._heap',
        'sklearn.utils._sorting',
        'sklearn.utils._vector_sentinel',
        'sklearn.neighbors._partition_nodes',
        'umap',
        'hdbscan',
        'PIL',
        'numpy',
        'networkx',
        'chinese_whispers',
        'scipy',
        'scipy.sparse',
        'scipy.sparse.csgraph',
        'scipy.sparse.csgraph._shortest_path',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'IPython',
        'jupyter',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PhotoSorterAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,      # GUI 앱이므로 콘솔 창 숨김
    icon='assets/icon.ico',
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PhotoSorterAI',
)
