@echo off
chcp 65001 >nul
:: 使用 venv 虚拟环境运行程序
set VENV_DIR=%~dp0venv
set PYTHONIOENCODING=utf-8

:: 激活虚拟环境并运行主程序
start "" "%VENV_DIR%\Scripts\pythonw.exe" src\main.py
