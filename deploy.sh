#!/bin/bash
# FRP Console 二次部署脚本（重部署现有项目，不装 Docker/不生成 .env）
#
# 全新安装请用 install.sh（自动装 Docker、生成 .env、多阶段构建）：
#   sudo bash install.sh
#
# 本脚本适合已在宿主机上部署过、镜像存在时的重构建/重启动：
#   1. 检查环境（docker、docker.sock）
#   2. 确保 /opt/frpc 配置目录存在且属主为容器内 appuser(1000)
#   3. 构建并启动容器（前端在容器内编译，宿主机无需 Node/npm）
#   4. 等待健康检查通过
#   5. 打印访问信息
set -e

# ==================== 颜色定义 ====================
RED='\033[91m'; GREEN='\033[92m'; YELLOW='\033[93m'; CYAN='\033[96m'; DIM='\033[2m'; RESET='\033[0m'

# ==================== 工具函数 ====================
log() {
    local level="$1" msg="$2" color=""
    case "$level" in
        INFO) color="$CYAN" ;; OK) color="$GREEN" ;; WARN) color="$YELLOW" ;; ERROR) color="$RED" ;;
    esac
    echo "${DIM}[$(date '+%H:%M:%S')]${RESET} ${color}[${level}]${RESET} ${msg}"
}
die() { log ERROR "$1"; exit 1; }

SUDO=""
[ "$(id -u)" -ne 0 ] && SUDO="sudo"

# ==================== 环境检查 ====================
log INFO "=== FRP Console 重部署开始 ==="

if ! command -v docker >/dev/null 2>&1; then
    die "未找到 docker 命令，请先安装 Docker（全新环境推荐: bash install.sh）"
fi

if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
else
    die "未找到 docker compose 插件"
fi
log OK "Docker Compose: ${COMPOSE_CMD}"

if ! docker info >/dev/null 2>&1; then
    die "Docker 守护进程未运行，请先启动 docker 服务"
fi
if [ ! -S /var/run/docker.sock ]; then
    die "未找到 /var/run/docker.sock，容器无法管理 frpc"
fi
log OK "docker 与 docker.sock 正常"

# 切到脚本所在目录（项目根目录）
cd "$(dirname "$0")" || die "无法切换到脚本所在目录"
[ -f docker-compose.yml ] || die "未找到 docker-compose.yml，请确认在项目根目录运行"
[ -f .env ] || { log WARN "未找到 .env，请先运行: bash install.sh"; exit 1; }

# ==================== 配置目录 ====================
log INFO "确保配置目录 /opt/frpc 存在且属主为容器内 appuser(1000)..."
if [ ! -d /opt/frpc ]; then
    $SUDO mkdir -p /opt/frpc
fi
if ! $SUDO chown -R 1000:1000 /opt/frpc 2>/dev/null; then
    log WARN "无法 chown /opt/frpc，请手动执行: sudo chown -R 1000:1000 /opt/frpc"
fi
$SUDO chmod 755 /opt/frpc 2>/dev/null || true
log OK "配置目录就绪"

# ==================== 清理旧容器 ====================
if docker ps -a --format '{{.Names}}' | grep -q '^frp-console$'; then
    log WARN "移除旧容器 frp-console..."
    docker rm -f frp-console
fi

# ==================== 构建并启动 ====================
log INFO "构建并启动容器（前端在容器内编译，首次可能较慢）..."
$COMPOSE_CMD up -d --build || die "容器启动失败，请查看上方日志"

# ==================== 等待健康检查 ====================
log INFO "等待健康检查..."
MAX_WAIT=180; WAITED=0; HEALTHY=false
while [ $WAITED -lt $MAX_WAIT ]; do
    STATUS=$(docker inspect --format='{{.State.Health.Status}}' frp-console 2>/dev/null || echo "starting")
    case "$STATUS" in
        healthy) HEALTHY=true; break ;;
        unhealthy) log ERROR "健康检查失败"; exit 1 ;;
    esac
    sleep 3; WAITED=$((WAITED+3)); printf "${DIM}.${RESET}"
done
echo ""
[ "$HEALTHY" = "true" ] && log OK "健康检查通过" || log WARN "等待超时，请查看 docker logs frp-console"

# ==================== 打印信息 ====================
PORT=$(grep -E '^PORT=' .env | tail -1 | cut -d= -f2 | tr -d '[:space:]')
PORT=${PORT:-7600}
HOST_IP=$(hostname -I 2>/dev/null | awk '{print $1}'); [ -z "$HOST_IP" ] && HOST_IP="127.0.0.1"
USER=$(grep -E '^ADMIN_USER=' .env | tail -1 | cut -d= -f2 | tr -d '[:space:]'); [ -z "$USER" ] && USER="admin"
echo ""
log OK "=== 部署完成 ==="
echo "访问地址: http://${HOST_IP}:${PORT}"
echo "登录用户: ${USER}（密码见 .env 的 ADMIN_PASSWORD）"
echo "查看日志: docker logs -f frp-console"