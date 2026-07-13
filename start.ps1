# 智能报价系统 - 启动脚本 (PowerShell)
# 启动后端和前端服务，并打开浏览器

$ErrorActionPreference = "Stop"
$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $rootDir "backend"
$frontendDir = Join-Path $rootDir "frontend"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "    智能报价系统 (Smart Quotation System)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ========== 1. 启动后端 ==========
Write-Host "[1/3] 正在启动后端服务..." -ForegroundColor Yellow

$pythonCmd = "python"
try {
    $null = Get-Command python -ErrorAction Stop
}
catch {
    try {
        $null = Get-Command py -ErrorAction Stop
        $pythonCmd = "py"
    }
    catch {
        Write-Host "[错误] 未找到 Python，请确保已安装 Python 3.9+" -ForegroundColor Red
        Read-Host "按回车键退出"
        exit 1
    }
}

# 启动后端（新窗口）
$backendJob = Start-Process -WindowStyle Normal -PassThru -FilePath "cmd.exe" -ArgumentList "/c", "cd /d `"$backendDir`" && set PYTHONPATH=$backendDir && $pythonCmd -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
Write-Host "后端进程 ID: $($backendJob.Id)" -ForegroundColor Gray

# 等待后端启动
Write-Host "等待后端服务启动..." -ForegroundColor Gray
$maxRetries = 15
$retryCount = 0
$backendReady = $false
while ($retryCount -lt $maxRetries) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $backendReady = $true
            break
        }
    }
    catch {
        # 还没准备好
    }
    $retryCount++
    Write-Host "." -NoNewline -ForegroundColor Gray
    Start-Sleep -Seconds 1
}
if (-not $backendReady) {
    Write-Host ""
    Write-Host "[警告] 后端启动可能超时，请检查 http://127.0.0.1:8000/api/health" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "[完成] 后端服务已启动 (http://127.0.0.1:8000)" -ForegroundColor Green
Write-Host ""

# ========== 2. 启动前端 ==========
Write-Host "[2/3] 正在启动前端服务..." -ForegroundColor Yellow

$frontendJob = Start-Process -WindowStyle Normal -PassThru -FilePath "cmd.exe" -ArgumentList "/c", "cd /d `"$frontendDir`" && npm run dev"
Write-Host "前端进程 ID: $($frontendJob.Id)" -ForegroundColor Gray

Start-Sleep -Seconds 5
Write-Host "[完成] 前端服务已启动" -ForegroundColor Green
Write-Host ""

# ========== 3. 打开浏览器 ==========
Write-Host "[3/3] 正在打开浏览器..." -ForegroundColor Yellow
Start-Process "http://localhost:5173"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "    启动完成！" -ForegroundColor Cyan
Write-Host ""
Write-Host "    前端地址: http://localhost:5173" -ForegroundColor White
Write-Host "    后端地址: http://localhost:8000" -ForegroundColor White
Write-Host "    API文档:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "按任意键关闭此窗口（后端和前端将继续运行）" -ForegroundColor Gray
Write-Host "提示：关闭窗口后，可在任务管理器中结束相关进程" -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
