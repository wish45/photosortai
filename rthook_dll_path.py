"""PyInstaller runtime hook: ensure bundled DLLs are findable on Windows."""

import os
import sys

if sys.platform == 'win32':
    # Add the application directory to DLL search path.
    # This ensures bundled msvcp140.dll, vcruntime140.dll, etc. are found
    # even on clean Windows installs without VC++ Redistributable.
    app_dir = os.path.dirname(sys.executable)

    # SetDllDirectory (Win32 API) — highest priority
    try:
        import ctypes
        ctypes.windll.kernel32.SetDllDirectoryW(app_dir)
    except Exception:
        pass

    # AddDllDirectory (Win8+) — adds to search list
    try:
        import ctypes
        ctypes.windll.kernel32.AddDllDirectory(app_dir)
    except Exception:
        pass

    # Also prepend to PATH as fallback
    os.environ['PATH'] = app_dir + os.pathsep + os.environ.get('PATH', '')
