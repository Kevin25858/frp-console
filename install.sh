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

# 下载函数（带镜像源切换）
download_with_mirror() {
    local url=$1
    local output=$2
    
    if curl -fsSL --connect-timeout 10 --max-time 60 "$url" -o "$output" 2>/dev/null; then
        return 0
    fi
    return 1
}

# 从多个源下载文件
download_from_mirrors() {
    local filename=$1
    local output=$2
    
    # 镜像源列表（jsDelivr 最快，放第一个）
    local mirrors=(
        "https://cdn.jsdelivr.net/gh/Kevin25858/frp-console@main/$filename"
        "https://raw.githubusercontent.com/Kevin25858/frp-console/main/$filename"
        "https://ghproxy.com/https://raw.githubusercontent.com/Kevin25858/frp-console/main/$filename"
        "https://mirror.ghproxy.com/https://raw.githubusercontent.com/Kevin25858/frp-console/main/$filename"
        "https://hub.gitmirror.com/https://raw.githubusercontent.com/Kevin25858/frp-console/main/$filename"
        "https://ghps.cc/https://raw.githubusercontent.com/Kevin25858/frp-console/main/$filename"
        "https://gh.api.99988866.xyz/https://raw.githubusercontent.com/Kevin25858/frp-console/main/$filename"
    )
    
    for mirror in "${mirrors[@]}"; do
        info "尝试从 $mirror 下载..."
        if download_with_mirror "$mirror" "$output"; then
            info "下载成功！"
            return 0
        fi
    done
    
    error "所有镜像源都下载失败"
    return 1
}

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
    # 尝试多个 Docker 安装脚本镜像
    if ! curl -fsSL https://get.docker.com | sh 2>/dev/null; then
        warn "官方脚本失败，尝试镜像..."
        curl -fsSL https://mirror.ghproxy.com/https://raw.githubusercontent.com/docker/docker-install/master/install.sh | sh
    fi
    systemctl enable docker
    systemctl start docker
fi

if ! command -v docker-compose &> /dev/null; then
    info "安装 Docker Compose..."
    # 尝试多个镜像源
    if ! curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose 2>/dev/null; then
        curl -L "https://ghproxy.com/https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    fi
    chmod +x /usr/local/bin/docker-compose
fi

# 4. 下载 frpc（使用 jsDelivr 加速）
info "下载 frpc..."
FRPC_URL="https://cdn.jsdelivr.net/gh/Kevin25858/frp-console@main/bin/frpc"

if ! download_with_mirror "$FRPC_URL" "/usr/local/bin/frpc"; then
    error "无法下载 frpc"
    exit 1
fi

chmod +x /usr/local/bin/frpc
info "frpc 下载成功"