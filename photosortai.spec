# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for PhotoSorterAI — macOS build."""

import os
from pathlib import Path

block_cipher = None

# InsightFace model path — CI local dir or user home
_local_models = os.path.join(SPECPATH, 'insightface_models')
insightface_models = (
    _local_models if os.path.isdir(_local_models)
    else str(Path.home() / '.insightface')
)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        (insightface_models, 'insightface'),
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
        'numpy.core',
        'numpy.core.multiarray',
        'numpy.core._multiarray_umath',
        'numpy.core.numeric',
        'numpy.linalg',
        'numpy.fft',
        'numpy.random',
        'networkx',
        'scipy',
        'scipy.sparse',
        'scipy.sparse.csgraph',
        'scipy.sparse.csgraph._shortest_path',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Unused insightface submodules with broken Cython deps
        'insightface.thirdparty.face3d',
        'insightface.thirdparty.face3d.mesh',
        'insightface.thirdparty.face3d.mesh.cython',
        'insightface.thirdparty.face3d.mesh.cython.mesh_core_cython',
        # Unused heavy packages
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
