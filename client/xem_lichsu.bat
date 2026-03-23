@echo off
REM ============================================
REM  Xem lich su upload (10 lan gan nhat)
REM ============================================

echo.
echo ========================================
echo   LICH SU UPLOAD (10 lan gan nhat)
echo ========================================
echo.

set SCRIPT_DIR=%~dp0
set HISTORY_FILE=%SCRIPT_DIR%upload_history.json

REM --- Tim Python ---
set PYTHON_CMD=python
if exist "%SCRIPT_DIR%python_path.txt" set /p PYTHON_CMD=<"%SCRIPT_DIR%python_path.txt"

if not exist "%HISTORY_FILE%" (
    echo Chua co lich su upload nao.
    echo Chay auto_upload.py hoac test_upload.bat truoc.
    pause
    exit /b 0
)

"%PYTHON_CMD%" -c "import json,os;f=open(r'%HISTORY_FILE%','r',encoding='utf-8');h=json.load(f);f.close();entries=h[-10:];print();[print(f'  [{e[\"timestamp\"]}] {\"OK\" if e[\"status\"]==\"success\" else \"FAIL\" if e[\"status\"]==\"error\" else \"TEST\" if e[\"status\"]==\"dry-run\" else \"NONE\":5s} | Win: {e.get(\"windows_user\",\"?\"):10s} | PC: {e.get(\"computer\",\"?\"):15s} | User: {e.get(\"username\",\"?\"):15s} | Gui: {e.get(\"records_sent\",0):>4d} | Luu: {e.get(\"records_saved\",0):>4d}' + (f' | Loi: {e[\"errors\"]}' if e.get('errors') else '')) for e in entries];print(f'\n  Tong: {len(h)} lan upload trong lich su')"

echo.
echo ========================================
echo   File log:    %SCRIPT_DIR%upload.log
echo   File JSON:   %HISTORY_FILE%
echo ========================================
echo.

pause
