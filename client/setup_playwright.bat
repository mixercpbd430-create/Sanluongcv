@echo off
chcp 65001 >nul
title Cài đặt Playwright cho SharePoint Downloader
echo ============================================================
echo   CÀI ĐẶT PLAYWRIGHT (SharePoint Download)
echo ============================================================
echo.

cd /d "%~dp0"

:: Kiểm tra Python
set PYTHON_CMD=python
if exist "%~dp0python_path.txt" set /p PYTHON_CMD=<"%~dp0python_path.txt"

echo [1/3] Kiểm tra Python...
"%PYTHON_CMD%" --version 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Không tìm thấy Python!
    echo         Vui lòng cài Python hoặc cập nhật python_path.txt
    pause
    exit /b 1
)

echo.
echo [2/3] Cài đặt package playwright...
"%PYTHON_CMD%" -m pip install playwright --quiet
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Cài playwright thất bại!
    pause
    exit /b 1
)

echo.
echo [3/3] Tải Chromium browser (không cần quyền admin)...
"%PYTHON_CMD%" -m playwright install chromium
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Tải Chromium thất bại!
    echo         Thử chạy lại với quyền admin.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   CÀI ĐẶT THÀNH CÔNG!
echo   Chromium đã được tải về (không cần quyền admin).
echo   Bạn có thể sử dụng chức năng SharePoint trong uploader.
echo ============================================================
echo.
pause
