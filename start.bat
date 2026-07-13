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

:: 查找 Python
set PYTHON_CMD=python
where python >nul 2>nul
if errorlevel 1 (
    where py >nul 2>nul
    if errorlevel 1 (
        echo [错误] 未找到 Python，请确保已安装 Python 3.9+
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=py
    )
)

:: 启动后端
start "智能报价-后端" cmd /c "cd /d "%~dp0backend" && set PYTHONPATH=%~dp0backend && %PYTHON_CMD% -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: 等待后端启动
echo 等待后端服务启动...
:wait_loop
timeout /t 2 /nobreak >nul
>nul 2>&1 curl -s http://127.0.0.1:8000/api/health
if errorlevel 1 (
    echo 正在启动...
    goto wait_loop
)
echo [完成] 后端服务已启动 (http://127.0.0.1:8000)
echo.

echo [2/3] 正在启动前端服务...
echo.
cd /d "%~dp0frontend"

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
