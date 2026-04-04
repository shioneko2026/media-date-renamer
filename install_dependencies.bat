@echo off
setlocal

:: MediaRenamer - install_dependencies.bat
:: Installs required Python packages via pip.

echo Checking for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not on PATH.
    echo Download Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

python --version
echo.

echo Installing required packages...
echo.

pip install pymediainfo PyQt6 Pillow pillow-heif
if %errorlevel% neq 0 (
    echo.
    echo ERROR: One or more packages failed to install.
    echo Check your internet connection or pip setup.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Dependencies installed successfully!
echo.
echo  NOTE: pymediainfo requires the MediaInfo library (DLL).
echo  If video date reading fails, download and install MediaInfo from:
echo  https://mediaarea.net/en/MediaInfo/Download/Windows
echo  (choose the installer, not the CLI version)
echo.
echo  NOTE: pillow-heif enables HEIC image support.
echo  If it failed to install, .heic files will be skipped gracefully.
echo ============================================================
echo.
pause
endlocal
