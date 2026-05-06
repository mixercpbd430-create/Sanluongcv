@echo off
REM ============================================
REM  Cai dat Task Scheduler tu dong gui du lieu
REM  KHONG CAN QUYEN ADMIN
REM  Ho tro nhieu profile tren 1 may tinh
REM  Tao 2 task: 6:00 va 6:30, co chay bu
REM ============================================
REM  Su dung:
REM    install_schedule.bat                  (dung config.json)
REM    install_schedule.bat mixer            (dung config_mixer.json)
REM    install_schedule.bat pellet_mini      (dung config_pellet_mini.json)
REM    install_schedule.bat pellet_feedmill  (dung config_pellet_feedmill.json)
REM ============================================

echo.
echo =============================================
echo   Cai dat tu dong gui du lieu 6:00 va 6:30
echo   Co chay bu neu may bat muon
echo   (Khong can quyen Admin)
echo =============================================
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
    set TASK_BASE=SanLuong_AutoUpload
    set CONFIG_FILE=%SCRIPT_DIR%config.json
    set PROFILE_ARG=
    echo Profile: mac dinh (config.json)
) else (
    set TASK_BASE=SanLuong_AutoUpload_%PROFILE%
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
    echo     "server_url": "https://api.binhduongfeedmill.com",
    echo     "username": "ten user",
    echo     "password": "mat khau",
    echo     "folder": "D:/duong/dan/folder/Excel"
    echo   }
    pause
    exit /b 1
)

echo Script: %SCRIPT_DIR%auto_upload.py %PROFILE_ARG%
echo.

REM ─── Task 1: 6:00 ─────────────────────────────
set TASK1=%TASK_BASE%_0600
echo [1/2] Tao task %TASK1% (6:00)...
schtasks /create /tn "%TASK1%" /tr "\"%PYTHON_CMD%\" \"%SCRIPT_DIR%auto_upload.py\" %PROFILE_ARG%" /sc daily /st 06:00 /f /rl limited

if %errorlevel% equ 0 (
    powershell -Command "try { $t = Get-ScheduledTask '%TASK1%'; $t.Settings.StartWhenAvailable = $true; Set-ScheduledTask -InputObject $t | Out-Null; Write-Host '      [OK] 6:00 + chay bu' } catch { Write-Host '      [CANH BAO] Khong bat duoc chay bu' }"
) else (
    echo      [LOI] Khong tao duoc task 6:00!
)

REM ─── Task 2: 6:30 ─────────────────────────────
set TASK2=%TASK_BASE%_0630
echo [2/2] Tao task %TASK2% (6:30)...
schtasks /create /tn "%TASK2%" /tr "\"%PYTHON_CMD%\" \"%SCRIPT_DIR%auto_upload.py\" %PROFILE_ARG%" /sc daily /st 06:30 /f /rl limited

if %errorlevel% equ 0 (
    powershell -Command "try { $t = Get-ScheduledTask '%TASK2%'; $t.Settings.StartWhenAvailable = $true; Set-ScheduledTask -InputObject $t | Out-Null; Write-Host '      [OK] 6:30 + chay bu' } catch { Write-Host '      [CANH BAO] Khong bat duoc chay bu' }"
) else (
    echo      [LOI] Khong tao duoc task 6:30!
)

REM ─── Ket qua ──────────────────────────────────
echo.
echo =============================================
echo   Cai dat thanh cong!
echo   Task 1: %TASK1% - 6:00 sang
echo   Task 2: %TASK2% - 6:30 sang
echo   Chay bu: CO (neu may bat muon)
echo =============================================
echo.
echo Xem trong Task Scheduler:
echo   taskschd.msc - Task Scheduler Library
echo   - %TASK1%
echo   - %TASK2%
echo.
echo De xoa tat ca task:
echo   schtasks /delete /tn "%TASK1%" /f
echo   schtasks /delete /tn "%TASK2%" /f
echo.

pause
