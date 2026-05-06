@echo off
chcp 65001 >nul
title Update Data - San Luong App

echo ============================================================
echo   IMPORT DU LIEU TU EXCEL VAO DATABASE
echo ============================================================

cd /d "%~dp0"

:: Create Update folder if not exists
if not exist "Update" (
    mkdir "Update"
    echo [*] Da tao folder Update\
)

:: Count Excel files
set COUNT=0
for %%f in ("Update\*.xlsx" "Update\*.xlsm") do set /a COUNT+=1

if %COUNT%==0 (
    echo.
    echo [!] Khong tim thay file Excel nao trong folder Update\
    echo     Hay copy file PL*.xlsx, MIXER*.xlsx vao:
    echo     %~dp0Update\
    echo.
    pause
    exit /b
)

echo.
echo [*] Tim thay %COUNT% file Excel trong folder Update\
echo.

:: Check if venv exists, activate it
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

set PYTHONIOENCODING=utf-8

echo [*] Dang doc file Excel va cap nhat database...
echo.

python database.py "%~dp0Update"

echo.
echo ============================================================
echo   HOAN TAT! Du lieu da duoc cap nhat.
echo   Neu app dang chay, nhan nut "Lam moi" tren dashboard.
echo ============================================================
echo.

pause
