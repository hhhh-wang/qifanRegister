@echo off
chcp 65001 >nul
setlocal

echo ===============================
echo 🔨 开始构建 7FGame 自动注册 EXE
echo ===============================

REM --- 定位到当前脚本目录（防止从别处双击）---
cd /d %~dp0

REM --- 清理旧构建 ---
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /f /q *.spec

REM --- 使用 python -m，避免找不到 pyinstaller ---
python -m PyInstaller ^
  -F ^
  --clean ^
  --noconsole ^
  --add-data "pic;pic" ^
  --add-data "slide_debug;slide_debug" ^
  --add-data "captcha_recognizer;captcha_recognizer" ^
  launch_7fgame.py

IF ERRORLEVEL 1 (
    echo.
    echo ❌ 构建失败，请检查上方错误信息
    pause
    exit /b 1
)

echo.
echo ✅ 构建完成！
echo ✅ EXE 路径：dist\launch_7fgame.exe
echo ===============================
pause 