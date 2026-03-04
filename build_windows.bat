@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo  PhotoSorterAI - Windows Build Script
echo ============================================================
echo.

REM ============================================================
REM  Step 0: Check and Install Python
REM ============================================================
echo [0/5] Checking Python installation...

python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
    echo   Python !PYVER! found.
    goto :python_ready
)

echo   Python not found. Installing Python 3.11 automatically...
echo.

REM Download Python installer
set PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
set PYTHON_INSTALLER=%TEMP%\python-3.11.9-amd64.exe

echo   Downloading Python 3.11.9...
powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%'" 2>nul
if not exist "%PYTHON_INSTALLER%" (
    echo   ERROR: Download failed. Check your internet connection.
    echo   Manual download: %PYTHON_URL%
    pause
    exit /b 1
)

echo   Installing Python 3.11.9 (this may take a minute)...
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_doc=0

if errorlevel 1 (
    echo   ERROR: Python installation failed.
    echo   Try installing manually from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Refresh PATH in current session
set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"

REM Verify installation
python --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Python installed but not found in PATH.
    echo   Close this window, open a new CMD, and run build_windows.bat again.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo   Python !PYVER! installed successfully!

del "%PYTHON_INSTALLER%" >nul 2>&1

:python_ready
echo.

REM ============================================================
REM  Step 1: Create virtual environment
REM ============================================================
echo [1/5] Creating virtual environment...
if exist venv (
    echo   Existing venv found, removing...
    rmdir /s /q venv
)
python -m venv venv
call venv\Scripts\activate.bat

REM ============================================================
REM  Step 2: Install dependencies
REM ============================================================
echo [2/5] Installing dependencies...
pip install --upgrade pip setuptools wheel >nul 2>&1
pip install -r requirements-win.txt
pip install pyinstaller

REM ============================================================
REM  Step 3: Download InsightFace model
REM ============================================================
echo [3/5] Downloading InsightFace model (buffalo_l, ~300MB first time)...
python -c "from insightface.app import FaceAnalysis; app = FaceAnalysis(name='buffalo_l'); app.prepare(ctx_id=0)"

REM ============================================================
REM  Step 4: Build with PyInstaller
REM ============================================================
echo [4/5] Building with PyInstaller...
pyinstaller photosortai_win.spec --clean --noconfirm

if not exist "dist\PhotoSorterAI\PhotoSorterAI.exe" (
    echo   ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  PyInstaller build complete!
echo  Output: dist\PhotoSorterAI\PhotoSorterAI.exe
echo ============================================================
echo.

REM ============================================================
REM  Step 5: Create installer with Inno Setup (optional)
REM ============================================================
echo [5/5] Creating installer with Inno Setup...
where iscc >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    iscc installer.iss
    echo.
    echo ============================================================
    echo  Installer created!
    echo  Output: installer_output\PhotoSorterAI_Setup_1.0.0.exe
    echo ============================================================
) else (
    echo.
    echo [SKIP] Inno Setup not found.
    echo   Install from: https://jrsoftware.org/isdl.php
    echo   Then run: iscc installer.iss
    echo.
    echo   Portable version is ready:
    echo     dist\PhotoSorterAI\PhotoSorterAI.exe
)

echo.
echo ============================================================
echo  BUILD COMPLETE!
echo ============================================================
echo.
echo  To run the app:
echo    dist\PhotoSorterAI\PhotoSorterAI.exe
echo.
pause
