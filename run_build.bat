@echo off
chcp 65001 >nul
echo === Сборка ArtDeck в .exe (PyInstaller) ===
python build.py
echo.
pause
