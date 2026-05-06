@echo off
cd /d "%~dp0"
set PYTHON_CMD=python
if exist "%~dp0python_path.txt" set /p PYTHON_CMD=<"%~dp0python_path.txt"
"%PYTHON_CMD%" uploader.py --profile pellet_feedmill
pause
