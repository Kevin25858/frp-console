#!/bin/bash
# FRP 客户端安装脚本
# 用于在宿主机上安装和配置 frpc

set -e

# 默认配置
FRP_VERSION="0.52.3"
INSTALL_DIR="/opt/frp-client"
CONFIG_DIR="/etc/frp-client"
WEB_CONSOLE_URL=""
CLIENT_ID=""
API_TOKEN=""

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印信息
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助
show_help() {
    cat << EOF
FRP 客户端安装脚本

用法: $0 [选项]

选项:
    -u, --url URL           Web 控制台地址 (必需)
    -i, --client-id ID      客户端 ID (必需)
    -t, --token TOKEN       API Token (必需)
    -v, --version VERSION   FRP 版本 (默认: $FRP_VERSION)
    -h, --help              显示此帮助

示例:
    $0 -u http://192.168.1.100:7600 -i 1 -t mysecrettoken
EOF
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--url)
            WEB_CONSOLE_URL="$2"
            shift 2
            ;;
        -i|--client-id)
            CLIENT_ID="$2"
            shift 2
            ;;
        -t|--token)
            API_TOKEN="$2"
            shift 2
            ;;
        -v|--version)
            FRP_VERSION="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 验证必需参数
if [[ -z "$WEB_CONSOLE_URL" ]] || [[ -z "$CLIENT_ID" ]] || [[ -z "$API_TOKEN" ]]; then
    error "缺少必需参数"
    show_help
    exit 1
fi

info "开始安装 frpc..."
info "Web 控制台: $WEB_CONSOLE_URL"
info "客户端 ID: $CLIENT_ID"

# 检测架构
ARCH=$(uname -m)
case $ARCH in
    x86_64)
        FRP_ARCH="amd64"
        ;;
    aarch64|arm64)
        FRP_ARCH="arm64"
        ;;
    armv7l)
        FRP_ARCH="arm"
        ;;
    *)
        error "不支持的架构: $ARCH"
        exit 1
        ;;
esac

info "检测到架构: $ARCH"

# 创建目录
info "创建安装目录..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"

# 下载 frp
cd /tmp
FRP_PACKAGE="frp_${FRP_VERSION}_linux_${FRP_ARCH}"
FRP_TAR="${FRP_PACKAGE}.tar.gz"
FRP_URL="https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/${FRP_TAR}"

if [[ -f "$FRP_TAR" ]]; then
    info "发现已下载的 frp 包，跳过下载"
else
    info "下载 frp v${FRP_VERSION}..."
    wget -q --show-progress "$FRP_URL" -O "$FRP_TAR" || {
        error "下载失败"
        exit 1
    }
fi

# 解压
info "解压 frp..."
tar -xzf "$FRP_TAR"
cp "${FRP_PACKAGE}/frpc" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/frpc"

# 创建配置同步脚本
cat > "$INSTALL_DIR/sync-config.sh" << 'SCRIPT_EOF'
#!/bin/bash
# 配置同步脚本

INSTALL_DIR="/opt/frp-client"
CONFIG_DIR="/etc/frp-client"
WEB_CONSOLE_URL="{{WEB_CONSOLE_URL}}"
CLIENT_ID="{{CLIENT_ID}}"
API_TOKEN="{{API_TOKEN}}"

# 拉取配置
fetch_config() {
    local config_file="$CONFIG_DIR/frpc.toml"
    local temp_file="$CONFIG_DIR/frpc.toml.tmp"
    
    # 从 Web 控制台拉取配置
    if ! curl -s -H "Authorization: Bearer $API_TOKEN" \
         "$WEB_CONSOLE_URL/api/configs/$CLIENT_ID/export" > "$temp_file"; then
        echo "[$(date)] 拉取配置失败" >> "$CONFIG_DIR/sync.log"
        return 1
    fi
    
    # 检查配置是否有变化
    if [[ -f "$config_file" ]] && diff -q "$config_file" "$temp_file" > /dev/null 2>&1; then
        # 配置没有变化
        rm "$temp_file"
        return 0
    fi
    
    # 更新配置
    mv "$temp_file" "$config_file"
    echo "[$(date)] 配置已更新" >> "$CONFIG_DIR/sync.log"
    
    # 重启 frpc
    systemctl restart frpc-client
    echo "[$(date)] frpc 已重启" >> "$CONFIG_DIR/sync.log"
    
    return 0
}

# 执行同步
fetch_config
SCRIPT_EOF

# 替换变量
sed -i "s|{{WEB_CONSOLE_URL}}|$WEB_CONSOLE_URL|g" "$INSTALL_DIR/sync-config.sh"
sed -i "s|{{CLIENT_ID}}|$CLIENT_ID|g" "$INSTALL_DIR/sync-config.sh"
sed -i "s|{{API_TOKEN}}|$API_TOKEN|g" "$INSTALL_DIR/sync-config.sh"
chmod +x "$INSTALL_DIR/sync-config.sh"

# 创建 systemd 服务文件
cat > /etc/systemd/system/frpc-client.service << EOF
[Unit]
Description=FRP Client
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$CONFIG_DIR
ExecStart=$INSTALL_DIR/frpc -c $CONFIG_DIR/frpc.toml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 创建配置同步定时任务（每分钟检查一次）
cat > /etc/systemd/system/frpc-config-sync.service << EOF
[Unit]
Description=FRP Config Sync
After=network.target

[Service]
Type=oneshot
ExecStart=$INSTALL_DIR/sync-config.sh
EOF

cat > /etc/systemd/system/frpc-config-sync.timer << EOF
[Unit]
Description=FRP Config Sync Timer

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min

[Install]
WantedBy=timers.target
EOF

# 首次拉取配置
info "首次拉取配置..."
if ! "$INSTALL_DIR/sync-config.sh"; then
    warn "首次拉取配置失败，将在定时任务中重试"
fi

# 启动服务
info "启动 frpc 服务..."
systemctl daemon-reload
systemctl enable frpc-client
systemctl enable frpc-config-sync.timer
systemctl start frpc-client
systemctl start frpc-config-sync.timer

# 清理临时文件
rm -rf "/tmp/${FRP_PACKAGE}" "/tmp/${FRP_TAR}"

info "安装完成！"
echo ""
echo "服务状态:"
systemctl status frpc-client --no-pager
systemctl status frpc-config-sync.timer --no-pager
echo ""
echo "查看日志:"
echo "  frpc 日志: journalctl -u frpc-client -f"
echo "  同步日志: $CONFIG_DIR/sync.log"
echo ""
echo "管理命令:"
echo "  启动: systemctl start frpc-client"
echo "  停止: systemctl stop frpc-client"
echo "  重启: systemctl restart frpc-client"
echo "  状态: systemctl status frpc-client"
