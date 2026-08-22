@echo off
chcp 65001 >nul
cd /d "%~dp0"
title AI Agent Platform 2.0.0

set "VENV_DIR=%CD%\.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
if exist "%PYTHON_EXE%" goto check_dependencies

where py >nul 2>nul
if not errorlevel 1 (
  echo 首次启动：正在创建虚拟环境...
  py -m venv "%VENV_DIR%"
  goto venv_created
)

where python >nul 2>nul
if not errorlevel 1 (
  echo 首次启动：正在创建虚拟环境...
  python -m venv "%VENV_DIR%"
  goto venv_created
)

echo 未找到 Python。请先安装 Python 3.11 或更高版本。
pause
exit /b 1

:venv_created
if not exist "%PYTHON_EXE%" (
  echo 虚拟环境创建失败。
  pause
  exit /b 1
)

:check_dependencies
"%PYTHON_EXE%" -c "import fastapi, uvicorn, litellm, chromadb, playwright, bs4" >nul 2>nul
if not errorlevel 1 goto run

echo 首次启动：正在安装项目依赖，这可能需要几分钟...
"%PYTHON_EXE%" -m pip install --disable-pip-version-check -e "%CD%"
if errorlevel 1 (
  echo.
  echo 依赖安装失败，请检查网络后重新运行本文件。
  pause
  exit /b 1
)

:run
"%PYTHON_EXE%" launcher.py
if %ERRORLEVEL% NEQ 0 (
  echo.
  echo 启动失败，请检查上方错误信息。
  pause
)
