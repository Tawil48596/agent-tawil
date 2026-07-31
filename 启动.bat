@echo off
chcp 65001 >nul
cd /d "%~dp0"
title AI Agent Platform 0.1.1

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
if exist "%PYTHON_EXE%" goto run

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  set "PYTHON_EXE=py"
  goto run
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  set "PYTHON_EXE=python"
  goto run
)

echo 未找到 Python。请先安装 Python 3.11 或在项目中创建 .venv。
pause
exit /b 1

:run
"%PYTHON_EXE%" launcher.py
if %ERRORLEVEL% NEQ 0 (
  echo.
  echo 启动失败，请检查上方错误信息。
  pause
)
