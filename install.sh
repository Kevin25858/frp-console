#!/bin/bash
# ============================================================
# FRP Console 一键安装脚本（通用 Linux 版）
#
# 特性：
#   - 自动检测发行版并安装 Docker / Docker Compose（也可跳过）
#   - 宿主机无需 Node/npm（前端在容器内多阶段构建）
#   - 自动创建 /opt/frpc 配置目录并设置属主
#   - 自动生成安全的 .env（随机 SECRET_KEY / API_TOKEN）
#   - 自动获取 docker 组 GID 写入 .env
#   - 构建启动容器，等待健康检查，打印访问信息
#
# 用法：
#   bash install.sh             # 交互式
#   bash install.sh --no-docker # 宿主机已装 Docker，跳过安装
#   bash install.sh --yes       # 所有确认默认为是
# ============================================================
set -e

# ==================== 配置 ====================
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIGS_DIR="/opt/frpc"
CONFIG_OWNER="1000:1000"          # 容器内 appuser 的 UID:GID

AUTO_YES=""
SKIP_DOCKER=""

# ==================== 颜色 & 工具 ====================
RED='\033[91m'; GREEN='\033[92m'; YELLOW='\033[93m'; CYAN='\033[96m'; DIM='\033[2m'; RESET='\033[0m'

log() { local l="$1" m="$2" c=""; case "$l" in INFO)c="$CYAN";;OK)c="$GREEN";;WARN)c="$YELLOW";;ERR)c="$RED";;esac; echo "${DIM}[$(date '+%H:%M:%S')]${RESET} ${c}[${l}]${RESET} ${m}"; }
die() { log ERR "$1"; exit 1; }

# Root 检测：若非 root，尝试用 sudo 包裹需要提权的命令
use_sudo() {
    if [ "$(id -u)" -eq 0 ]; then
        echo ""
    else
        echo "sudo"
    fi
}
SUDO="$(use_sudo)"
need_sudo() { [ -n "$SUDO" ]; }

# 解析参数
for arg in "$@"; do
    case "$arg" in
        --yes|-y) AUTO_YES=1 ;;
        --no-docker|--skip-docker) SKIP_DOCKER=1 ;;
        --help|-h)
            sed -n '3,14p' "${BASH_SOURCE[0]}" | sed 's/^# //;s/^#//'
            exit 0 ;;
    esac
done

confirm() {
    [ -n "$AUTO_YES" ] && return 0
    read -rp "$1 [y/N] " ans
    [[ "$ans" =~ ^[Yy]$ ]]
}

# ==================== 1. 检查/安装 Docker ====================
echo ""
log INFO "=== FRP Console 安装开始 ==="
log INFO "项目目录: $PROJECT_DIR"

install_docker() {
    if need_sudo; then
        die "需要 root 权限安装 Docker，请用 root 运行 或 先手动安装 Docker"
    fi

    if command -v apt-get >/dev/null 2>&1; then
        log INFO "检测到 apt（Debian/Ubuntu），安装 Docker..."
        apt-get update -y
        [ ! -x /usr/bin/curl ] && apt-get install -y curl
        curl -fsSL https://get.docker.com | sh
    elif command -v dnf >/dev/null 2>&1; then
        log INFO "检测到 dnf（Fedora/RHEL），安装 Docker..."
        dnf -y install docker docker-compose-plugin
        systemctl enable --now docker
    elif command -v yum >/dev/null 2>&1; then
        log INFO "检测到 yum（CentOS），安装 Docker..."
        curl -fsSL https://get.docker.com | sh
        systemctl enable --now docker
    elif command -v apk >/dev/null 2>&1; then
        log INFO "检测到 apk（Alpine），安装 Docker..."
        apk add --no-cache docker docker-cli-compose
        rc-update add docker default; service docker start
    elif command -v pacman >/dev/null 2>&1; then
        log INFO "检测到 pacman（Arch），安装 Docker..."
        pacman -Sy --noconfirm docker docker-compose
        systemctl enable --now docker
    else
        die "无法识别的包管理器，请手动安装 Docker 后重试"
    fi
}

if [ -z "$SKIP_DOCKER" ]; then
    if ! command -v docker >/dev/null 2>&1; then
        log WARN "未检测到 Docker。"
        if confirm "是否自动安装 Docker？"; then
            install_docker
        else
            die "未安装 Docker，请先安装后重试（或用 --skip-docker 手动跳过）"
        fi
    else
        log OK "已检测到 Docker"
    fi
else
    log INFO "跳过 Docker 安装（--skip-docker）"
fi

# 校验 docker 命令
if ! command -v docker >/dev/null 2>&1; then
    die "docker 命令不可用"
fi

# compose 命令检测
if docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE="docker-compose"
else
    die "未找到 docker compose，请安装 Docker Compose 插件"
fi
log OK "Docker Compose: $COMPOSE"

# docker daemon 是否运行 / 当前用户是否有权限
if ! docker info >/dev/null 2>&1; then
    if [ -n "$SUDO" ] && $SUDO docker info >/dev/null 2>&1; then
        log WARN "当前用户无权限访问 docker，使用 sudo 继续（后续命令可能需 sudo）"
    else
        log WARN "Docker 守护进程未运行或当前用户无权限，尝试启动..."
        $SUDO systemctl start docker 2>/dev/null || true
        sleep 2
        if ! docker info >/dev/null 2>&1; then
            die "Docker 不可用，请检查 docker 服务状态"
        fi
    fi
fi
log OK "Docker 守护进程可用"

if [ ! -S /var/run/docker.sock ]; then
    die "未找到 /var/run/docker.sock，容器无法管理 frpc"
fi
log OK "docker.sock 可用"

# ==================== 2. 工作目录 / 检出 ====================
cd "$PROJECT_DIR"

# 关键配置文件检查
for f in docker-compose.yml Dockerfile requirements.txt frontend/package.json app/app.py; do
    if [ ! -e "$f" ]; then
        die "缺少必需文件: $f，请确保在项目根目录运行本脚本"
    fi
done
log OK "项目文件完整"

# ==================== 3. .env ====================
log "配置 .env ..."

# make .env (if missing)
if [ ! -f .env ]; then
    [ -f .env.example ] && cp .env.example .env
    log OK ".env 已创建（默认密码和管理员见下）"
else
    log OK ".env 已存在"
fi

gen_secret() { # $1 = bytes -> hex 字符串
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex "$1"
    elif command -v xxd >/dev/null 2>&1; then
        head -c "$1" /dev/urandom | xxd -p -c 256
    else
        head -c "$1" /dev/urandom | tr -dc 'a-f0-9'
    fi
}

# ensure_env key default_value  —— 键不存在则追加默认
ensure_env() {
    local key="$1" val="$2"
    if ! grep -qE "^${key}=" .env; then
        printf "%s=%s\n" "$key" "$val" >> .env
    fi
}
# ensure_placeholder: 若 KEY 是占位符/空，则替换为 $2（新值）
ensure_placeholder() {
    local key="$1" newval="$2"
    local cur
    cur=$(grep -E "^${key}=" .env | tail -1 | cut -d= -f2-)
    if [ -z "$cur" ] || echo "$cur" | grep -qE "change_me|CHANGE_ME|^$"; then
        # Linux/macOS 兼容 sed 原地替换
        if [ "$(uname)" = "Darwin" ]; then
            sed -i '' "s#^${key}=.*#${key}=${newval}#" .env
        else
            sed -i "s#^${key}=.*#${key}=${newval}#" .env
        fi
    fi
}

# 基础键缺失则补默认
ensure_env "PORT" "7600"
ensure_env "TZ" "Asia/Shanghai"
ensure_env "ADMIN_USER" "admin"
ensure_env "ADMIN_PASSWORD" "CHANGE_ME"
ensure_env "FORCE_HTTPS" "false"

# 关键密钥：占位符/空则自动生成随机值
ensure_placeholder "SECRET_KEY" "$(gen_secret 32)"
ensure_placeholder "API_TOKEN" "$(gen_secret 16)"
ensure_placeholder "ADMIN_PASSWORD" "$(gen_secret 24)"
log OK "密钥/密码已生成（见 .env）"

# 固定 DOCKER_GID（优先取 socket 属组，其次 docker 组，最后兜底）
GID_DOCKER=$(stat -c '%g' /var/run/docker.sock 2>/dev/null || echo "")
if [ -z "$GID_DOCKER" ] || [ "$GID_DOCKER" = "0" ]; then
    GID_DOCKER="$(getent group docker 2>/dev/null | cut -d: -f3 || echo "")"
fi
[ -z "$GID_DOCKER" ] && GID_DOCKER="988"
ensure_env "DOCKER_GID" "$GID_DOCKER"
# 若已有值但为空/无效，则覆写为探测值
cur_gid=$(grep -E "^DOCKER_GID=" .env | tail -1 | cut -d= -f2- | tr -d '[:space:]')
if [ -z "$cur_gid" ] || [ "$cur_gid" = "0" ] || [ "$cur_gid" = "999" ]; then
    if [ "$(uname)" = "Darwin" ]; then
        sed -i '' "s/^DOCKER_GID=.*/DOCKER_GID=${GID_DOCKER}/" .env
    else
        sed -i "s/^DOCKER_GID=.*/DOCKER_GID=${GID_DOCKER}/" .env
    fi
fi
log OK "docker 组 GID = $GID_DOCKER"

# ==================== 4. 配置目录 /opt/frpc ====================
log INFO "准备配置目录 $CONFIGS_DIR ..."
if [ ! -d "$CONFIGS_DIR" ]; then
    $SUDO mkdir -p "$CONFIGS_DIR"
    log OK "已创建 $CONFIGS_DIR"
else
    log OK "$CONFIGS_DIR 已存在"
fi
# 属主改为容器内 appuser(1000)，web 容器才能读写
if ! $SUDO chown -R "$CONFIG_OWNER" "$CONFIGS_DIR" 2>/dev/null; then
    log WARN "无法 chown $CONFIGS_DIR（可能无权限），请手动执行:"
    log WARN "  sudo chown -R 1000:1000 $CONFIGS_DIR"
fi
$SUDO chmod 755 "$CONFIGS_DIR" 2>/dev/null || true
log OK "配置目录权限已设置"

# ==================== 5. 清理旧容器 ====================
if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q '^frp-console$'; then
    log WARN "发现旧容器 frp-console，正在移除..."
    docker rm -f frp-console
fi

# ==================== 6. 构建并启动 ====================
log INFO "构建并启动容器（前端在容器内编译，可能需要几分钟）..."
$COMPOSE up -d --build
log OK "容器已启动"

# ==================== 7. 等待健康检查 ====================
log INFO "等待健康检查..."
MAX_WAIT=180
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    STATUS=$(docker inspect --format='{{.State.Health.Status}}' frp-console 2>/dev/null || echo starting)
    case "$STATUS" in
        healthy) log OK "健康检查通过"; HEALTHY=1; break;;
        unhealthy) log ERR "健康检查失败"; log ERR "查看日志: docker logs frp-console"; exit 1;;
    esac
    sleep 3; WAITED=$((WAITED+3))
    printf "${DIM}.${RESET}"
done
[ -n "$HEALTHY" ] || log WARN "等待超时，请查看 docker ps / docker logs frp-console"

# ==================== 8. 打印信息 ====================
echo ""
PORT=$(grep -E '^PORT=' .env | tail -1 | cut -d= -f2 | tr -d '[:space:]' || echo 7600)
HOST_IP=$(hostname -I 2>/dev/null | awk '{print $1}'); [ -z "$HOST_IP" ] && HOST_IP="127.0.0.1"
PASS=$(grep -E '^ADMIN_PASSWORD=' .env | tail -1 | cut -d= -f2)
USER=$(grep -E '^ADMIN_USER=' .env | tail -1 | cut -d= -f2 | tr -d '[:space:]'); [ -z "$USER" ] && USER="admin"

log "===== 部署完成 ====="
echo ""
echo "${GREEN}访问地址:${RESET}"
echo "  本机:   http://localhost:${PORT}"
echo "  局域网: http://${HOST_IP}:${PORT}"
echo ""
echo "${CYAN}登录信息:${RESET}"
echo "  用户名: ${USER:-admin}"
echo "  密码:   ${PASS}"
echo ""
echo "${DIM}常用命令:${RESET}"
echo "  查看日志:   docker logs -f frp-console"
echo "  重启服务:   docker restart frp-console"
echo "  停止服务:   ${COMPOSE} down"
echo "  卸载:       docker compose down && docker rmi frp-console-frp-console"
echo ""
log INFO "首次使用请在 frp-console 内添加客户端；配置存放于 $CONFIGS_DIR"