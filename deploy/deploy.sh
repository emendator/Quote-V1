#!/usr/bin/env bash
# ============================================================
# 智能报价系统 - Ubuntu 云服务器一键部署脚本
#
# 前提：
#   1. 项目已通过 git clone 到 /opt/smart-quotation
#      git clone https://github.com/emendator/Quote.git /opt/smart-quotation
#   2. 系统为 Ubuntu 20.04 / 22.04 / 24.04
#
# 端口约定：
#   - 外部访问端口（Nginx）默认 8085（用户指定，访问 http://IP:8085；
#     内地未备案建议使用非 80 端口）
#   - 后端 FastAPI 内部监听 127.0.0.1:8008（仅内网由 Nginx 反代；
#     避开其它项目后端已用的 8003/8004/8005/8006，避免端口冲突）
#
# 用法：
#   cd /opt/smart-quotation
#   sudo bash deploy/deploy.sh 8085      # 外部访问 http://IP:8085
#
# 会执行：
#   ① 系统依赖  ② Node.js  ③ 后端依赖  ④ 前端构建
#   ⑤ systemd 服务  ⑥ Nginx  ⑦ 防火墙
# ============================================================
set -euo pipefail

# 外部访问端口（Nginx）：默认 8085；内地未备案建议用非 80 端口（如 8085）
PORT="${1:-8085}"
case "$PORT" in
    ''|*[!0-9]*) echo "[ERROR] 端口必须是数字，例如: sudo bash deploy/deploy.sh 8085"; exit 1;;
esac

# 后端内部端口：8008（外部 Nginx 用 8085，后端内部避开其它项目已用的 8003-8006）
BACKEND_PORT="8008"
APP_DIR="/opt/smart-quotation"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"
DEPLOY_DIR="$APP_DIR/deploy"
SERVICE_NAME="smart-quotation"

echo "============================================================"
echo "  智能报价系统 - 云服务器一键部署"
echo "  外部端口: $PORT    后端内部端口: $BACKEND_PORT"
echo "============================================================"

if [ ! -d "$BACKEND_DIR" ]; then
    echo "[ERROR] 找不到 $BACKEND_DIR"
    echo "        请先把项目 git clone 到 $APP_DIR 后再运行本脚本"
    exit 1
fi

# ---------- 1. 系统依赖 ----------
echo ""
echo "[1/7] 更新系统并安装基础依赖..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y nginx python3 python3-venv python3-pip curl git

# ---------- 2. Node.js ----------
echo ""
echo "[2/7] 安装 Node.js 20 LTS..."
if ! command -v node >/dev/null 2>&1; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi
echo "  Node.js: $(node --version)"
# 国内服务器加速 npm 下载
npm config set registry https://registry.npmmirror.com 2>/dev/null || true

# ---------- 3. 后端依赖 ----------
echo ""
echo "[3/7] 创建 Python 虚拟环境并安装依赖..."
cd "$BACKEND_DIR"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
# 国内服务器加速 pip 下载
.venv/bin/pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple 2>/dev/null || true
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

# ---------- 4. 前端构建 ----------
echo ""
echo "[4/7] 构建前端页面..."
cd "$FRONTEND_DIR"
npm install --no-audit --no-fund
npm run build

# ---------- 5. systemd 后端服务 ----------
echo ""
echo "[5/7] 配置后端 systemd 服务..."
cp "$DEPLOY_DIR/$SERVICE_NAME.service" /etc/systemd/system/$SERVICE_NAME.service
# 后端监听端口固定为 BACKEND_PORT
sed -i "s/--port [0-9]*/--port $BACKEND_PORT/" /etc/systemd/system/$SERVICE_NAME.service
chown -R www-data:www-data "$APP_DIR"
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

# ---------- 6. Nginx ----------
echo ""
echo "[6/7] 配置 Nginx..."
cp "$DEPLOY_DIR/nginx.conf" /etc/nginx/sites-available/$SERVICE_NAME
# 按指定端口替换监听端口
sed -i "s/listen 80;/listen $PORT;/" /etc/nginx/sites-available/$SERVICE_NAME
# 反代地址固定为 BACKEND_PORT
sed -i "s|proxy_pass http://127.0.0.1:8004;|proxy_pass http://127.0.0.1:$BACKEND_PORT;|" /etc/nginx/sites-available/$SERVICE_NAME
ln -sf /etc/nginx/sites-available/$SERVICE_NAME /etc/nginx/sites-enabled/$SERVICE_NAME
nginx -t
systemctl enable nginx
systemctl reload nginx

# ---------- 7. 防火墙 ----------
echo ""
echo "[7/7] 配置防火墙..."
if command -v ufw >/dev/null 2>&1; then
    ufw allow OpenSSH
    ufw allow "$PORT/tcp"
    ufw --force enable
fi

# 获取公网 IP（用于最后提示）
IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || curl -s --max-time 5 ip.sb 2>/dev/null || echo "你的服务器公网IP")
if [ "$PORT" = "80" ]; then
    ACCESS_URL="http://$IP"
else
    ACCESS_URL="http://$IP:$PORT"
fi

echo ""
echo "============================================================"
echo "  ✅ 部署完成！"
echo "------------------------------------------------------------"
echo "  访问地址:  $ACCESS_URL"
echo "  登录账号:  admin"
echo "  登录密码:  ***REMOVED-PASSWORD***   公司: ***REMOVED-COMPANY***  数据库密码: ***REMOVED-PASSWORD***"
echo "  后端内部:  http://127.0.0.1:$BACKEND_PORT"
echo ""
echo "  常用命令:"
echo "    查看后端日志:  journalctl -u $SERVICE_NAME -f"
echo "    重启后端:      systemctl restart $SERVICE_NAME"
echo "    重载 Nginx:    nginx -t && systemctl reload nginx"
echo "============================================================"
