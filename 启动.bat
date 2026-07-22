@echo off
chcp 65001 >nul
title 智能报价系统

echo ============================================
echo     智能报价系统 (Smart Quotation System)
echo ============================================
echo.
echo [1/3] 正在启动后端服务...
echo.

cd /d "%~dp0backend"

rem 自动检测 Python 解释器路径
set PYTHON_CMD=

rem 1. 优先使用项目虚拟环境
if exist "%~dp0.venv\Scripts\python.exe" set PYTHON_CMD=%~dp0.venv\Scripts\python.exe
if defined PYTHON_CMD echo [检测] 使用虚拟环境: %PYTHON_CMD% & goto :found_python

rem 2. 尝试 PATH 中的 python
for /f "delims=" %%i in ('where python 2^>nul') do set PYTHON_CMD=%%i
if defined PYTHON_CMD echo [检测] 使用系统 Python: %PYTHON_CMD% & goto :found_python

rem 3. 尝试 PATH 中的 py (Python Launcher)
for /f "delims=" %%i in ('where py 2^>nul') do set PYTHON_CMD=%%i
if defined PYTHON_CMD echo [检测] 使用 Python Launcher: %PYTHON_CMD% & goto :found_python

rem 4. 检查常见安装路径
if exist "%LOCALAPPDATA%\Programs\Python\" (
    for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
        if exist "%%d\python.exe" set PYTHON_CMD=%%d\python.exe
    )
)
if defined PYTHON_CMD echo [检测] 使用: %PYTHON_CMD% & goto :found_python

for %%d in (C:\Python313 C:\Python312 C:\Python311 C:\Python310 C:\Python39) do (
    if exist "%%d\python.exe" set PYTHON_CMD=%%d\python.exe
)
if defined PYTHON_CMD echo [检测] 使用: %PYTHON_CMD% & goto :found_python

rem 5. 均未找到，报错
echo [错误] 未找到 Python，请确保已安装 Python 3.9+
echo.
echo 已尝试以下方式：
echo   - 项目虚拟环境 .venv\Scripts\python.exe
echo   - PATH 环境变量中的 python/py
echo   - %%LOCALAPPDATA%%\Programs\Python\Python*
echo   - 常见安装目录 C:\Python39~C:\Python313
pause
exit /b 1

:found_python
echo [检测] Python路径: %PYTHON_CMD%
echo.

:: 安装/检查 Python 依赖
if exist "%~dp0.venv" (
    echo [安装] 检测到虚拟环境，跳过依赖安装（如需重新安装请删除 .venv 文件夹）
) else (
    echo [安装] 正在检查并安装 Python 依赖...
    "%PYTHON_CMD%" -m pip install -r "%~dp0backend\requirements.txt" -q
    if errorlevel 1 (
        echo [错误] Python 依赖安装失败！
        echo 请手动执行: cd backend ^&^& pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo [安装] Python 依赖安装完成
)
echo.

:: 启动后端（不使用 --reload，避免因文件监听器不稳定导致后端进程意外退出）
:: 如需开发模式（热重载），可将下面命令改为使用 --reload
start "智能报价-后端" cmd /c "cd /d "%~dp0backend" && set PYTHONPATH=%~dp0backend && "%PYTHON_CMD%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

:: 等待后端启动（最多等待 30 秒）
echo 等待后端服务启动...
set WAIT_COUNT=0
:wait_loop
timeout /t 2 /nobreak >nul
set /a WAIT_COUNT+=1
>nul 2>&1 curl -s http://127.0.0.1:8000/api/health
if errorlevel 1 (
    if %WAIT_COUNT% geq 15 (
        echo [错误] 后端启动超时，请检查:
        echo   - 是否已安装 Python 3.9+
        echo   - Python 依赖是否安装成功
        echo   - 端口 8000 是否被占用
        echo.
        echo 可右键 "启动.bat" ^> "以管理员身份运行" 重试
        pause
        exit /b 1
    )
    echo 正在启动...（%WAIT_COUNT%/15）
    goto wait_loop
)
echo [完成] 后端服务已启动 (http://127.0.0.1:8000)
echo.

echo [2/3] 正在启动前端服务...
echo.
cd /d "%~dp0frontend"

:: 检查/安装前端依赖
if not exist "node_modules" (
    echo [安装] 正在安装前端依赖（首次运行需要下载，请耐心等待）...
    call npm install
    if errorlevel 1 (
        echo [错误] 前端依赖安装失败！
        echo 请确保已安装 Node.js（https://nodejs.org）
        pause
        exit /b 1
    )
    echo [安装] 前端依赖安装完成
) else (
    echo [检测] 前端依赖已存在，跳过安装
)
echo.

:: 启动前端
start "智能报价-前端" cmd /c "cd /d "%~dp0frontend" && npm run dev"

echo 等待前端服务启动...
timeout /t 5 /nobreak >nul
echo [完成] 前端服务已启动
echo.

echo [3/3] 正在打开浏览器...
echo.
start http://localhost:5173

echo ============================================
echo     启动完成！
echo.
echo     前端地址: http://localhost:5173
echo     后端地址: http://localhost:8000
echo     API文档:  http://localhost:8000/docs
echo ============================================
echo.
echo 按任意键关闭此窗口（后端和前端将继续运行）
pause >nul
