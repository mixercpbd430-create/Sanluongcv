@echo off
chcp 65001 >nul
title San Luong Hang Ngay - Flask App

echo ============================================================
echo   SAN LUONG HANG NGAY - Starting...
echo ============================================================

cd /d "%~dp0"

:: Check if venv exists, activate it
if exist "venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo [!] No venv found, using system Python.
)

:: Install dependencies if needed
echo [*] Checking dependencies...
pip install -r requirements.txt --quiet

echo.
echo ============================================================
echo   App running at: http://localhost:5000
echo   Press Ctrl+C to stop
echo ============================================================
echo.

python app.py

pause
