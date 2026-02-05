@echo off
chcp 65001
:: 设置 Python 的路径，假设 python312 文件夹位于 D 盘
set PYTHON_DIR=%~dp0..\python312

:: %PYTHON_DIR%\python.exe --version

:: 使用 get_pip.py 安装 pip
@REM "%PYTHON_DIR%\python.exe" "%~dp0get_pip.py"

:: 设置 Scripts 目录到 PATH 中
set PATH=%PYTHON_DIR%\Scripts;%PATH%

:: echo %PATH%

@REM "%PYTHON_DIR%\python.exe" -m ensurepip --upgrade

:: 确认 pip 安装成功
"%PYTHON_DIR%\python.exe" -m pip --version

:: 安装依赖库
"%PYTHON_DIR%\python.exe" -m pip install opencv-python pandas numpy Pillow openpyxl tk ultralytics


echo 感谢等待， 环境初始化成功！！ 可以关闭此窗口
pause