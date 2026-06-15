@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
echo ============================================
echo  Steam Art Downloader (non-Steam games)
echo ============================================
echo.
python artdeck_cli.py %*
echo.
echo Done. If art was downloaded, restart Steam to see it.
echo This window will close in 4 seconds...
timeout /t 4 >nul
