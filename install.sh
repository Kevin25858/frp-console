#!/bin/bash
#
# FRP Console 一键安装脚本
# FRP 客户端多开管理控制台
#

set -e

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
NC=$'\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="frpc-console"
CONFIG_FILE="${APP_DIR}/frp-console.conf"
SYSTEMD_FILE="/etc/systemd/system/${APP_NAME}.service"
BINARY_NAME="frpc"

DEFAULT_PORT=7601
DEFAULT_USER="admin"
DEFAULT_PASS="ChangeMe123!@#"

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "请使用 sudo 运行此脚本"
        exit 1
    fi
}

check_system() {
    if [[ ! -f /etc/os-release ]]; then
        log_error "不支持的系统"
        exit 1
    fi
    
    if ! command -v python3 &> /dev/null; then
        log_info "安装 Python 3..."
        apt-get update && apt-get install -y python3 python3-pip
    fi
    
    if ! command -v wget &> /dev/null; then
        apt-get install -y wget
    fi
}

download_frpc() {
    log_info "下载 FRPC 二进制..."
    
    ARCH=$(uname -m)
    if [[ "$ARCH" == "x86_64" ]]; then
        FRPC_URL="https://github.com/fatedier/frp/releases/download/v0.52.3/frp_0.52.3_linux_amd64.tar.gz"
    elif [[ "$ARCH" == "aarch64" ]]; then
        FRPC_URL="https://github.com/fatedier/frp/releases/download/v0.52.3/frp_0.52.3_linux_arm64.tar.gz"
    else
        log_warn "未知架构，使用 amd64"
        FRPC_URL="https://github.com/fatedier/frp/releases/download/v0.52.3/frp_0.52.3_linux_amd64.tar.gz"
    fi
    
    cd /tmp
    wget -q "$FRPC_URL" -O frp.tar.gz
    tar -xzf frp.tar.gz
    mkdir -p ${APP_DIR}/frpc
    mv frp_*/${BINARY_NAME} ${APP_DIR}/frpc/
    chmod +x ${APP_DIR}/frpc/${BINARY_NAME}
    rm -rf frp.tar.gz frp_*
    
    log_info "FRPC 下载完成"
}

install_dependencies() {
    log_info "安装 Python 依赖..."
    pip3 install -q -r ${APP_DIR}/requirements.txt
}

create_config() {
    log_info "创建配置..."
    
    mkdir -p ${APP_DIR}/data ${APP_DIR}/logs ${APP_DIR}/clients
    
    if [[ ! -f "$CONFIG_FILE" ]]; then
        cat > "$CONFIG_FILE" << EOF
# FRP Console 配置文件
PORT=${DEFAULT_PORT}
ADMIN_USER=${DEFAULT_USER}
ADMIN_PASSWORD=${DEFAULT_PASS}
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
EOF
        chmod 600 "$CONFIG_FILE"
        log_info "配置文件已创建: $CONFIG_FILE"
    fi
}

create_command() {
    log_info "创建管理命令..."
    
    cp ${APP_DIR}/${APP_NAME} /usr/local/bin/${APP_NAME}
    chmod +x /usr/local/bin/${APP_NAME}
    
    log_info "命令已安装: ${APP_NAME}"
}

create_service() {
    log_info "创建系统服务..."
    
    cat > "$SYSTEMD_FILE" << EOF
[Unit]
Description=FRP Console - FRP Client Management Panel
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${APP_DIR}
EnvironmentFile=${CONFIG_FILE}
ExecStart=/usr/bin/python3 -m flask --app ${APP_DIR}/app/app.py run --host=0.0.0.0 --port=\${PORT}
Restart=always

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable ${APP_NAME}
    
    log_info "服务已配置"
}

main() {
    echo "================================"
    echo "  FRP Console 安装脚本"
    echo "  FRP 客户端多开管理控制台"
    echo "================================"
    echo ""
    
    check_root
    check_system
    
    if [[ ! -d "${APP_DIR}/frpc" ]]; then
        download_frpc
    fi
    
    install_dependencies
    create_config
    create_command
    create_service
    
    echo ""
    echo "================================"
    log_info "安装完成!"
    echo "================================"
    echo ""
    echo "启动控制台:"
    echo "  ${APP_NAME}"
    echo ""
    echo "配置文件: $CONFIG_FILE"
    echo ""
}

main "$@"
