#!/bin/bash
# FRP Console 一键安装脚本
# 在同一台服务器上部署 Web 管理端和 frpc

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 配置
INSTALL_DIR="/opt/frp-console"
FRP_VERSION="0.52.3"
ADMIN_PASSWORD=""
API_TOKEN=""

# 交互式配置
echo "========================================"
echo "  FRP Console 一键安装"
echo "========================================"
echo ""

read -p "请输入管理员密码: " ADMIN_PASSWORD
echo ""
read -p "请输入 API Token (用于 frpc 认证): " API_TOKEN
echo ""
read -p "请输入服务端口 [默认7600]: " PORT
PORT=${PORT:-7600}
echo ""

info "开始安装..."

# 1. 创建目录
info "创建安装目录..."
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# 2. 安装 Docker（如果没有）
if ! command -v docker &> /dev/null; then
    info "安装 Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

if ! command -v docker-compose &> /dev/null; then
    info "安装 Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# 3. 下载 frpc
info "下载 frpc..."
ARCH=$(uname -m)
case $ARCH in
    x86_64) FRP_ARCH="amd64" ;;
    aarch64|arm64) FRP_ARCH="arm64" ;;
    *) error "不支持的架构: $ARCH"; exit 1 ;;
esac

FRP_PACKAGE="frp_${FRP_VERSION}_linux_${FRP_ARCH}"
FRP_TAR="${FRP_PACKAGE}.tar.gz"
FRP_URL="https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/${FRP_TAR}"

wget -q "$FRP_URL" -O /tmp/$FRP_TAR
tar -xzf /tmp/$FRP_TAR -C /tmp
cp "/tmp/${FRP_PACKAGE}/frpc" /usr/local/bin/frpc
chmod +x /usr/local/bin/frpc
rm -rf "/tmp/${FRP_PACKAGE}" "/tmp/${FRP_TAR}"

# 4. 创建 docker-compose.yml
info "创建 Docker Compose 配置..."
cat > $INSTALL_DIR/docker-compose.yml << EOF
version: '3.8'

services:
  frp-console:
    image: ghcr.io/kevin25858/frp-console:latest
    container_name: frp-console
    restart: unless-stopped
    ports:
      - "${PORT}:7600"
    environment:
      - PORT=7600
      - ADMIN_PASSWORD=${ADMIN_PASSWORD}
      - SECRET_KEY=$(openssl rand -hex 32)
      - API_TOKEN=${API_TOKEN}
    volumes:
      - ./data:/app/data
EOF

# 5. 创建 frpc 配置同步脚本
info "创建配置同步服务..."
mkdir -p /etc/frp-client

cat > /usr/local/bin/frpc-sync.sh << 'SCRIPT'
#!/bin/bash
CONFIG_FILE="/etc/frp-client/frpc.toml"
TEMP_FILE="/etc/frp-client/frpc.toml.tmp"
LOG_FILE="/var/log/frpc-sync.log"

# 从 Web 端拉取配置
fetch_config() {
    # 获取第一个客户端的配置（简化版）
    if ! curl -s -H "Authorization: Bearer ${API_TOKEN}" \
         "http://localhost:${PORT}/api/configs/1/export" > "$TEMP_FILE" 2>/dev/null; then
        echo "[$(date)] 拉取配置失败" >> "$LOG_FILE"
        return 1
    fi
    
    # 检查配置是否有变化
    if [[ -f "$CONFIG_FILE" ]] && diff -q "$CONFIG_FILE" "$TEMP_FILE" > /dev/null 2>&1; then
        rm "$TEMP_FILE"
        return 0
    fi
    
    # 更新配置
    mv "$TEMP_FILE" "$CONFIG_FILE"
    echo "[$(date)] 配置已更新，重启 frpc" >> "$LOG_FILE"
    
    # 重启 frpc
    systemctl restart frpc
    
    return 0
}

fetch_config
SCRIPT
chmod +x /usr/local/bin/frpc-sync.sh

# 6. 创建 systemd 服务
info "创建 frpc systemd 服务..."

cat > /etc/systemd/system/frpc.service << EOF
[Unit]
Description=FRP Client
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/frpc -c /etc/frp-client/frpc.toml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/frpc-sync.service << EOF
[Unit]
Description=FRP Config Sync
After=network.target

[Service]
Type=oneshot
Environment="API_TOKEN=${API_TOKEN}"
Environment="PORT=${PORT}"
ExecStart=/usr/local/bin/frpc-sync.sh
EOF

cat > /etc/systemd/system/frpc-sync.timer << EOF
[Unit]
Description=FRP Config Sync Timer

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min

[Install]
WantedBy=timers.target
EOF

# 7. 启动 Web 端
info "启动 Web 管理端..."
docker-compose up -d

# 等待 Web 端启动
info "等待 Web 端启动..."
sleep 5

# 8. 首次拉取配置并启动 frpc
info "初始化 frpc 配置..."
API_TOKEN="${API_TOKEN}" PORT="${PORT}" /usr/local/bin/frpc-sync.sh || warn "首次拉取配置失败，将在定时任务中重试"

# 9. 启动 frpc 服务
info "启动 frpc 服务..."
systemctl daemon-reload
systemctl enable frpc
systemctl enable frpc-sync.timer
systemctl start frpc
systemctl start frpc-sync.timer

# 10. 完成
echo ""
echo "========================================"
echo "  安装完成！"
echo "========================================"
echo ""
echo "Web 管理界面: http://$(hostname -I | awk '{print $1}'):${PORT}"
echo "用户名: admin"
echo "密码: ${ADMIN_PASSWORD}"
echo ""
echo "管理命令:"
echo "  查看 frpc 状态: systemctl status frpc"
echo "  查看同步状态: systemctl status frpc-sync.timer"
echo "  查看日志: journalctl -u frpc -f"
echo "  重启 Web: cd ${INSTALL_DIR} && docker-compose restart"
echo ""
echo "注意:"
echo "  - Web 端使用 Docker 运行"
echo "  - frpc 使用 systemd 运行（独立于 Docker）"
echo "  - Docker 重启不会影响 frpc"
echo "  - 配置修改后约1分钟自动同步到 frpc"
echo ""
