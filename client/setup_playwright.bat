@echo off
chcp 65001 >nul
title Cai dat Playwright
echo ============================================================
echo   CAI DAT PLAYWRIGHT (SharePoint Download)
echo ============================================================
echo.
cd /d "%~dp0"
set PYTHON_CMD=python
if exist "%~dp0python_path.txt" (
    set /p PYTHON_CMD=<"%~dp0python_path.txt"
)
echo [1/3] Kiem tra Python...
"%PYTHON_CMD%" --version
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Khong tim thay Python!
    pause
    exit /b 1
)
echo.
echo [2/3] Cai dat package playwright...
"%PYTHON_CMD%" -m pip install playwright
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Cai playwright that bai!
    pause
    exit /b 1
)
echo.
echo [3/3] Tai Chromium browser...
"%PYTHON_CMD%" -m playwright install chromium
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Tai Chromium that bai!
    pause
    exit /b 1
)
echo.
echo ============================================================
echo   CAI DAT THANH CONG!
echo ============================================================
pause
