# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for PhotoSorterAI — Windows build."""

import os
import sys
import glob
from pathlib import Path

block_cipher = None

# ── MSVC Runtime DLL collection ──────────────────────────────────────────
# Clean Windows PCs may not have these. Bundle them from the build machine.
_msvc_dll_names = [
    'msvcp140.dll',
    'msvcp140_1.dll',
    'msvcp140_2.dll',
    'vcruntime140.dll',
    'vcruntime140_1.dll',
    'concrt140.dll',
    'vcomp140.dll',
]

msvc_binaries = []
_search_paths = [
    os.path.dirname(sys.executable),                                       # Python dir
    os.path.join(os.environ.get('SYSTEMROOT', r'C:\Windows'), 'System32'), # System32
    os.path.join(os.environ.get('SYSTEMROOT', r'C:\Windows'), 'SysWOW64'),
]

# Also search in Visual Studio paths
_vs_paths = glob.glob(r'C:\Program Files\Microsoft Visual Studio\*\*\VC\Redist\MSVC\*\x64\*.CRT')
_vs_paths += glob.glob(r'C:\Program Files (x86)\Microsoft Visual Studio\*\*\VC\Redist\MSVC\*\x64\*.CRT')
_search_paths.extend(_vs_paths)

for dll_name in _msvc_dll_names:
    for search_dir in _search_paths:
        dll_path = os.path.join(search_dir, dll_name)
        if os.path.isfile(dll_path):
            msvc_binaries.append((dll_path, '.'))
            print(f"  [MSVC] Found {dll_name} -> {dll_path}")
            break
    else:
        print(f"  [MSVC] WARNING: {dll_name} not found (may not be needed)")

# ── UCRT (Universal C Runtime) DLLs ─────────────────────────────────────
# Needed on older Windows (pre-10). Usually in Python's DLLs directory.
_ucrt_dir = os.path.join(os.path.dirname(sys.executable), 'DLLs')
ucrt_binaries = []
if os.path.isdir(_ucrt_dir):
    for dll in glob.glob(os.path.join(_ucrt_dir, 'api-ms-win-*.dll')):
        ucrt_binaries.append((dll, '.'))
    for dll in glob.glob(os.path.join(_ucrt_dir, 'ucrtbase*.dll')):
        ucrt_binaries.append((dll, '.'))

# Also check Windows SDK UCRT path
_ucrt_sdk = glob.glob(r'C:\Program Files (x86)\Windows Kits\10\Redist\*\ucrt\DLLs\x64')
for ucrt_path in _ucrt_sdk:
    for dll in glob.glob(os.path.join(ucrt_path, '*.dll')):
        ucrt_binaries.append((dll, '.'))

print(f"  [UCRT] Collected {len(ucrt_binaries)} UCRT DLLs")

# ── InsightFace model path ───────────────────────────────────────────────
_local_models = os.path.join(SPECPATH, 'insightface_models')
insightface_models = _local_models if os.path.isdir(_local_models) else os.path.join(Path.home(), '.insightface')

# ── Analysis ─────────────────────────────────────────────────────────────
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=msvc_binaries + ucrt_binaries,
    datas=[
        (insightface_models, 'insightface'),
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
        'numpy.core',
        'numpy.core.multiarray',
        'numpy.core._multiarray_umath',
        'numpy.core.numeric',
        'numpy.core.operand_flag_tests',
        'numpy.linalg',
        'numpy.fft',
        'numpy.random',
        'networkx',
        'chinese_whispers',
        'scipy',
        'scipy.sparse',
        'scipy.sparse.csgraph',
        'scipy.sparse.csgraph._shortest_path',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['rthook_dll_path.py'],
    excludes=[
        'insightface.thirdparty.face3d',
        'insightface.thirdparty.face3d.mesh',
        'insightface.thirdparty.face3d.mesh.cython',
        'insightface.thirdparty.face3d.mesh.cython.mesh_core_cython',
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
    console=False,
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
