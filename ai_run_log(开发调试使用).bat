@echo off
:: 设置 Python 的路径，假设 python312 文件夹位于 D  盘
set PYTHON_DIR=%~dp0python312

:: %PYTHON_DIR%\python.exe --version

"%PYTHON_DIR%\python.exe" src\main.py --log

pause
