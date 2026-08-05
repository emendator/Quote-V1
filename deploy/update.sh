#!/usr/bin/env bash
# ============================================================
# 智能报价系统 - 服务器更新脚本
#
# 前提：新代码已同步到 /opt/smart-quotation（git pull 即可）
# 用法：cd /opt/smart-quotation && sudo bash deploy/update.sh
# 效果：修复权限 → 重新构建前端 → 重启后端，使新代码生效
# ============================================================
set -euo pipefail

APP_DIR="/opt/smart-quotation"
FRONTEND_DIR="$APP_DIR/frontend"
SERVICE_NAME="smart-quotation"

echo "============================================================"
echo "  智能报价系统 - 更新服务"
echo "============================================================"

# 0. 修复权限（新拉取的代码属主可能是 root，data/ 需 www-data 可写）
echo "[0/3] 修复目录权限..."
chown -R www-data:www-data "$APP_DIR"

# 1. 重新构建前端
if [ -d "$FRONTEND_DIR" ]; then
    echo "[1/3] 重新构建前端..."
    cd "$FRONTEND_DIR"
    npm install --no-audit --no-fund
    npm run build
else
    echo "[1/3] 未找到前端目录，跳过前端构建"
fi

# 2. 重启后端服务
echo "[2/3] 重启后端服务..."
systemctl restart $SERVICE_NAME

# 3. 校验状态
echo "[3/3] 检查服务状态..."
systemctl --no-pager status $SERVICE_NAME --lines=3 || true

echo ""
echo "============================================================"
echo "  ✅ 更新完成！刷新浏览器即可（建议 Ctrl+F5 强刷）"
echo "============================================================"
