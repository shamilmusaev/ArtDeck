@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -c "import PIL" 2>nul || python -m pip install --quiet pillow
python -c "import webview" 2>nul || python -m pip install --quiet pywebview
start "" pythonw steam_art_app.py
