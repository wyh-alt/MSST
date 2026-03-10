@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

echo ============================================
echo   MSST WebUI - PyTorch 自动安装工具
echo ============================================
echo.

REM Detect Python
set PYTHON=
if exist "workenv\python.exe" (
    set PYTHON=workenv\python.exe
) else (
    where python >nul 2>&1
    if !errorlevel! equ 0 (
        set PYTHON=python
    ) else (
        echo [错误] 未找到 Python 环境
        echo 请确保 workenv\python.exe 存在或 Python 已添加到 PATH
        pause
        exit /b 1
    )
)

echo 使用 Python: %PYTHON%
%PYTHON% setup_pytorch.py

if !errorlevel! neq 0 (
    echo.
    echo [错误] PyTorch 安装失败，请查看上方错误信息
    pause
    exit /b 1
)

echo.
echo PyTorch 安装完成！
pause
