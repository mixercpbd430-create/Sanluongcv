@echo off
REM ============================================
REM  Test gui du lieu (DRY-RUN - khong gui that)
REM  Chi doc file Excel va kiem tra config
REM ============================================
REM  Su dung:
REM    test_upload.bat                  (test config.json)
REM    test_upload.bat mixer            (test config_mixer.json)
REM    test_upload.bat pellet_mini      (test config_pellet_mini.json)
REM    test_upload.bat pellet_feedmill  (test config_pellet_feedmill.json)
REM ============================================

echo.
echo ========================================
echo   TEST - Kiem tra doc file Excel
echo   (Khong gui len server)
echo ========================================
echo.

set SCRIPT_DIR=%~dp0
set PROFILE=%~1

REM --- Tim Python ---
set PYTHON_CMD=python
if exist "%SCRIPT_DIR%python_path.txt" (
    set /p PYTHON_CMD=<"%SCRIPT_DIR%python_path.txt"
    echo Python: %PYTHON_CMD%
)

REM Kiem tra Python ton tai
"%PYTHON_CMD%" --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Python!
    echo Tao file python_path.txt voi duong dan den python.exe
    echo Vi du: D:\Software\Python\python.exe
    pause
    exit /b 1
)

if "%PROFILE%"=="" (
    echo Profile: mac dinh
    "%PYTHON_CMD%" "%SCRIPT_DIR%auto_upload.py" --dry-run
) else (
    echo Profile: %PROFILE%
    "%PYTHON_CMD%" "%SCRIPT_DIR%auto_upload.py" --dry-run --profile %PROFILE%
)

echo.
echo ========================================
echo   Ket qua test hien thi o tren.
echo   Xem log day du: %SCRIPT_DIR%upload.log
echo   Xem lich su:    %SCRIPT_DIR%upload_history.json
echo ========================================
echo.

pause
