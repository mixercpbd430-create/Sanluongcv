@echo off
echo === Checking tkinter ===
"D:\Software\Nho\python-3.14.3-win-x64\x64\python.exe" -c "import tkinter; print('tkinter is working!')"
if %errorlevel% neq 0 (
    echo [ERROR] tkinter is NOT available. Please reinstall Python with tcl/tk option.
    pause
    exit /b 1
)

echo.
echo === Installing pandas and openpyxl ===
"D:\Software\Nho\python-3.14.3-win-x64\x64\python.exe" -m pip install pandas openpyxl

echo.
echo === Installing requests ===
"D:\Software\Nho\python-3.14.3-win-x64\x64\python.exe" -m pip install requests

echo.
echo === Done! All packages installed successfully ===
pause