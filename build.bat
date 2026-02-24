@echo off
chcp 65001 >nul
echo ============================================
echo   PCBA Thermal Mapper 打包腳本
echo ============================================
echo.

REM 使用專案內建的 Python312 環境
set PYTHON=%~dp0Python312\python.exe

REM 檢查 Python 是否存在
if not exist "%PYTHON%" (
    echo [ERROR] 找不到 Python312\python.exe
    echo 請確認 Python312 目錄存在
    pause
    exit /b 1
)

REM 檢查 PyInstaller 是否已安裝
"%PYTHON%" -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [INFO] 正在安裝 PyInstaller...
    "%PYTHON%" -m pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] PyInstaller 安裝失敗
        pause
        exit /b 1
    )
)

echo.
echo [INFO] 開始打包...
echo.

"%PYTHON%" -m PyInstaller ^
    --name "Thermal温度点位自动识别系统" ^
    --windowed ^
    --noconfirm ^
    --clean ^
    --runtime-hook runtime_hook.py ^
    --add-data "font;font" ^
    --add-data "config;config" ^
    --hidden-import openpyxl ^
    --hidden-import PIL ^
    --hidden-import cv2 ^
    --hidden-import numpy ^
    --hidden-import pandas ^
    --exclude-module yolo_v8 ^
    --exclude-module ultralytics ^
    --exclude-module torch ^
    --exclude-module torchvision ^
    --exclude-module matplotlib ^
    --exclude-module scipy ^
    --exclude-module pytest ^
    --exclude-module unittest ^
    --icon "Python312\DLLs\py.ico" ^
    src/main.py

if errorlevel 1 (
    echo.
    echo [ERROR] 打包失敗，請查看上方錯誤訊息
    pause
    exit /b 1
)

echo.
echo ============================================
echo   打包完成！
echo   輸出位置: dist\Thermal温度点位自动识别系统\
echo ============================================
echo.

REM 建立 logs 資料夾（預設空的）
if not exist "dist\Thermal温度点位自动识别系统\logs" (
    mkdir "dist\Thermal温度点位自动识别系统\logs"
)

echo [INFO] 可將 dist\Thermal温度点位自动识别系统\ 整個資料夾壓縮發佈
echo.
pause
