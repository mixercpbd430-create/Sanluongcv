@echo off
echo === Checking tkinter ===
python -c "import tkinter; print('tkinter is working!')"
if %errorlevel% neq 0 (
    echo [ERROR] tkinter is NOT available. Please reinstall Python with tcl/tk option.
    pause
    exit /b 1
)

echo.
echo === Installing pandas and openpyxl ===
pip install pandas openpyxl

echo.
echo === Installing requests ===
pip install requests

echo.
echo === Done! All packages installed successfully ===
pause