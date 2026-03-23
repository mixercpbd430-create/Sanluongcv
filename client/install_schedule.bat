@echo off
REM ============================================
REM  Cai dat Task Scheduler tu dong gui du lieu
REM  KHONG CAN QUYEN ADMIN
REM  Ho tro nhieu profile tren 1 may tinh
REM ============================================
REM  Su dung:
REM    install_schedule.bat                  (dung config.json)
REM    install_schedule.bat mixer            (dung config_mixer.json)
REM    install_schedule.bat pellet_mini      (dung config_pellet_mini.json)
REM    install_schedule.bat pellet_feedmill  (dung config_pellet_feedmill.json)
REM ============================================

echo.
echo ========================================
echo   Cai dat tu dong gui du lieu 6h sang
echo   (Khong can quyen Admin)
echo ========================================
echo.

REM Get the directory of this script
set SCRIPT_DIR=%~dp0

REM --- Tim Python ---
set PYTHON_CMD=python
if exist "%SCRIPT_DIR%python_path.txt" (
    set /p PYTHON_CMD=<"%SCRIPT_DIR%python_path.txt"
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

echo Python: %PYTHON_CMD%

REM Get profile from argument
set PROFILE=%~1
if "%PROFILE%"=="" (
    set TASK_NAME=SanLuong_AutoUpload
    set CONFIG_FILE=%SCRIPT_DIR%config.json
    set PROFILE_ARG=
    echo Profile: mac dinh (config.json)
) else (
    set TASK_NAME=SanLuong_AutoUpload_%PROFILE%
    set CONFIG_FILE=%SCRIPT_DIR%config_%PROFILE%.json
    set PROFILE_ARG=--profile %PROFILE%
    echo Profile: %PROFILE% (config_%PROFILE%.json)
)

REM Check if config file exists
if not exist "%CONFIG_FILE%" (
    echo.
    echo [LOI] Khong tim thay: %CONFIG_FILE%
    echo Tao file config truoc, vi du:
    echo   {
    echo     "server_url": "https://sanluongcv.onrender.com",
    echo     "username": "ten user",
    echo     "password": "mat khau",
    echo     "folder": "D:/duong/dan/folder/Excel"
    echo   }
    pause
    exit /b 1
)

echo Script: %SCRIPT_DIR%auto_upload.py %PROFILE_ARG%
echo Task:   %TASK_NAME%
echo.

REM Create the scheduled task (no admin needed with /rl limited)
echo Dang tao Task Scheduler...
schtasks /create /tn "%TASK_NAME%" /tr "\"%PYTHON_CMD%\" \"%SCRIPT_DIR%auto_upload.py\" %PROFILE_ARG%" /sc daily /st 06:00 /f /rl limited

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   Cai dat thanh cong!
    echo   Task: %TASK_NAME%
    echo   Thoi gian: 6:00 sang hang ngay
    echo ========================================
    echo.
    echo Xem trong Task Scheduler:
    echo   taskschd.msc - Task Scheduler Library
    echo   - %TASK_NAME%
    echo.
    echo De xoa task nay:
    echo   schtasks /delete /tn "%TASK_NAME%" /f
    echo.
) else (
    echo.
    echo [LOI] Khong tao duoc task!
    echo Thu lai hoac lien he admin.
)

pause
