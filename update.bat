@echo off
chcp 65001 >nul
title Update Data - San Luong App

echo ============================================================
echo   IMPORT DU LIEU TU EXCEL VAO DATABASE
echo   Quet tat ca folder va subfolder trong Update\
echo ============================================================

cd /d "%~dp0"

:: Create Update folder if not exists
if not exist "Update" (
    mkdir "Update"
    echo [*] Da tao folder Update\
)

:: Count subfolders
set FOLDER_COUNT=0
for /d %%d in ("Update\*") do set /a FOLDER_COUNT+=1

:: Count Excel files recursively (including subfolders)
set COUNT=0
for /r "Update" %%f in (*.xlsx *.xlsm) do (
    set "fname=%%~nxf"
    setlocal enabledelayedexpansion
    if not "!fname:~0,2!"=="~$" set /a COUNT+=1
    endlocal
)

if %COUNT%==0 (
    echo.
    echo [!] Khong tim thay file Excel nao trong folder Update\
    echo     Hay copy file PL*.xlsx, MIXER*.xlsx vao:
    echo     %~dp0Update\
    echo.
    echo     Cau truc folder:
    echo       Update\PL1 2024\PL1 1.2024.xlsx
    echo       Update\PL1 2025\PL1 1.2025.xlsx
    echo       Update\PL1 5.2026.xlsx
    echo       Update\MIXER T5.2026.xlsx
    echo.
    pause
    exit /b
)

echo.
echo [*] Tim thay %COUNT% file Excel trong %FOLDER_COUNT% subfolder
echo.

:: Check if venv exists, activate it
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

set PYTHONIOENCODING=utf-8

echo [*] Dang doc tat ca file Excel va cap nhat database...
echo     (Bao gom san luong, NVVH, LOSS tu 2024 den nay)
echo.

python database.py "%~dp0Update"

echo.
echo ============================================================
echo   HOAN TAT! Du lieu da duoc cap nhat.
echo   Neu app dang chay, nhan nut "Lam moi" tren dashboard.
echo ============================================================
echo.

pause
