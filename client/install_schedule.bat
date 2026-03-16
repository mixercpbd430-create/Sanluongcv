@echo off
REM ============================================
REM  Cài đặt Task Scheduler tự động gửi dữ liệu
REM  Chạy file này với quyền Administrator
REM ============================================

echo.
echo ========================================
echo   Cài đặt tự động gửi dữ liệu 6h sáng
echo ========================================
echo.

REM Get the directory of this script
set SCRIPT_DIR=%~dp0

REM Check if config.json exists
if not exist "%SCRIPT_DIR%config.json" (
    echo [LỖI] Chưa có config.json!
    echo Chạy uploader.py trước để cấu hình.
    pause
    exit /b 1
)

REM Find Python path
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [LỖI] Không tìm thấy Python!
    echo Cài Python từ https://python.org
    pause
    exit /b 1
)

for /f "delims=" %%i in ('where python') do set PYTHON_PATH=%%i

echo Python: %PYTHON_PATH%
echo Script: %SCRIPT_DIR%auto_upload.py
echo.

REM Create the scheduled task
echo Đang tạo Task Scheduler...
schtasks /create /tn "SanLuong_AutoUpload" /tr "\"%PYTHON_PATH%\" \"%SCRIPT_DIR%auto_upload.py\"" /sc daily /st 06:00 /f /rl highest

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   ✅ Cài đặt thành công!
    echo   Task: SanLuong_AutoUpload
    echo   Thời gian: 6:00 sáng hàng ngày
    echo ========================================
    echo.
    echo Xem trong Task Scheduler:
    echo   taskschd.msc → Task Scheduler Library
    echo   → SanLuong_AutoUpload
    echo.
) else (
    echo.
    echo [LỖI] Không tạo được task!
    echo Thử chạy lại với quyền Administrator.
    echo   Chuột phải → Run as administrator
)

pause
