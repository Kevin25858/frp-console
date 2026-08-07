#!/bin/bash
# FRP Console 一键部署脚本
# 用法：./deploy.sh
#
# 本脚本完成以下事情：
#   1. 检查环境（docker、docker.sock）
#   2. 创建 /opt/frpc 配置目录并设置权限
#   3. 自动获取宿主机 docker 组 GID，写入 .env
#   4. 构建并启动容器（含前端构建）
#   5. 等待健康检查通过
#   6. 打印访问信息
set -e

# ==================== 颜色定义 ====================
RED='\033[91m'
GREEN='\033[92m'
YELLOW='\033[93m'
CYAN='\033[96m'
DIM='\033[2m'
RESET='\033[0m'

# ==================== 工具函数 ====================
log() {
    # 格式：[时间] [级别] 消息
    local level="$1"
    local msg="$2"
    local color=""
    case "$level" in
        INFO)    color="$CYAN" ;;
        OK)      color="$GREEN" ;;
        WARN)    color="$YELLOW" ;;
        ERROR)   color="$RED" ;;
        *)       color="" ;;
    esac
    local time_str
    time_str=$(date '+%H:%M:%S')
    echo "${DIM}[${time_str}]${RESET} ${color}[${level}]${RESET} ${msg}"
}

die() {
    log ERROR "$1"
    exit 1
}

# ==================== 步骤 1：环境检查 ====================
log INFO "=== FRP Console 一键部署开始 ==="
echo ""

log INFO "[1/7] 检查环境..."

# 检查 docker 命令
if ! command -v docker >/dev/null 2>&1; then
    die "未找到 docker 命令，请先安装 Docker"
fi

# 检查 docker compose 子命令（v2）或 docker-compose（v1）
if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
else
    die "未找到 docker compose，请安装 Docker Compose"
fi
log OK "Docker Compose: ${COMPOSE_CMD}"

# 检查 docker 服务是否运行
if ! docker info >/dev/null 2>&1; then
    die "Docker 守护进程未运行，请先启动 docker 服务"
fi
log OK "Docker 守护进程运行中"

# 检查 docker.sock
if [ ! -S /var/run/docker.sock ]; then
    die "未找到 /var/run/docker.sock，容器无法管理 frpc"
fi
log OK "docker.sock 可用"

# 切到脚本所在目录（项目根目录）
cd "$(dirname "$0")" || die "无法切换到脚本所在目录"

# 检查 docker-compose.yml
if [ ! -f docker-compose.yml ]; then
    die "未找到 docker-compose.yml，请确认在项目根目录运行"
fi

# 检查 .env
if [ ! -f .env ]; then
    log WARN "未找到 .env，从 .env.example 复制"
    cp .env.example .env
    log WARN "请编辑 .env 修改默认密码后再运行本脚本"
    log WARN "5 秒后继续（按 Ctrl+C 中止）..."
    sleep 5
fi

echo ""

# ==================== 步骤 2：配置目录 ====================
log INFO "[2/7] 准备配置目录..."

# 创建 /opt/frpc（frpc 配置文件存放处）
# 由容器挂载使用，UID 1000 是容器内 appuser 的用户 ID
if [ ! -d /opt/frpc ]; then
    mkdir -p /opt/frpc
    log OK "已创建 /opt/frpc"
else
    log OK "/opt/frpc 已存在"
fi

# 设置目录所有者为 1000（容器内 appuser 的 UID）
# 这样容器能读写配置文件
chown -R 1000:1000 /opt/frpc 2>/dev/null || {
    log WARN "无法 chown /opt/frpc（需要 root 权限），尝试 sudo..."
    sudo chown -R 1000:1000 /opt/frpc || log WARN "sudo 失败，容器可能无法写配置文件"
}
chmod 755 /opt/frpc

echo ""

# ==================== 步骤 3：构建前端 ====================
log INFO "[3/7] 构建前端（Dockerfile 使用本地 dist，不在容器内构建）..."

# 检查 node 和 npm
if ! command -v npm >/dev/null 2>&1; then
    die "未找到 npm，请先安装 Node.js（用于构建前端）"
fi

# 检查 frontend/dist 是否已存在
if [ -f frontend/dist/index.html ]; then
    log OK "frontend/dist 已存在，跳过构建（删除后重新运行可强制重建）"
else
    log INFO "安装前端依赖..."
    (cd frontend && npm install) || die "前端依赖安装失败"
    log INFO "构建前端..."
    (cd frontend && npm run build) || die "前端构建失败"
    log OK "前端构建完成"
fi

echo ""

# ==================== 步骤 4：设置 DOCKER_GID ====================
log INFO "[4/7] 获取 Docker 组 GID..."

# 从 docker.sock 文件获取组 ID
# 容器需要加入这个组才能访问 docker.sock
DOCKER_GID=$(stat -c '%g' /var/run/docker.sock 2>/dev/null || echo "")

if [ -z "$DOCKER_GID" ]; then
    die "无法获取 docker.sock 的 GID"
fi
log OK "宿主机 docker 组 GID: ${DOCKER_GID}"

# 写入或更新 .env 中的 DOCKER_GID
if grep -q '^DOCKER_GID=' .env; then
    # 已存在，替换
    if [ "$(uname)" = "Darwin" ]; then
        # macOS 的 sed 需要 -i ''
        sed -i '' "s/^DOCKER_GID=.*/DOCKER_GID=${DOCKER_GID}/" .env
    else
        sed -i "s/^DOCKER_GID=.*/DOCKER_GID=${DOCKER_GID}/" .env
    fi
    log OK "已更新 .env 中 DOCKER_GID=${DOCKER_GID}"
else
    # 不存在，追加
    echo "" >> .env
    echo "# Docker 组 GID（由 deploy.sh 自动设置）" >> .env
    echo "DOCKER_GID=${DOCKER_GID}" >> .env
    log OK "已写入 .env: DOCKER_GID=${DOCKER_GID}"
fi

echo ""

# ==================== 步骤 4：清理旧容器 ====================
log INFO "[5/7] 清理旧容器（如有）..."

# 如果存在同名容器，先移除（避免名称冲突）
if docker ps -a --format '{{.Names}}' | grep -q '^frp-console$'; then
    log WARN "发现旧容器 frp-console，正在移除..."
    docker rm -f frp-console
    log OK "旧容器已移除"
else
    log OK "无旧容器需要清理"
fi

echo ""

# ==================== 步骤 5：构建并启动 ====================
log INFO "[6/7] 构建并启动容器..."

# --build：强制重新构建镜像
# -d：后台运行
$COMPOSE_CMD up -d --build

if [ $? -ne 0 ]; then
    die "容器启动失败，请查看上方日志"
fi

echo ""

# ==================== 步骤 6：等待健康检查 ====================
log INFO "[7/7] 等待健康检查通过..."

# 最多等 60 秒
MAX_WAIT=60
WAITED=0
HEALTHY=false

while [ $WAITED -lt $MAX_WAIT ]; do
    # 检查容器状态
    STATUS=$(docker inspect --format='{{.State.Health.Status}}' frp-console 2>/dev/null || echo "starting")

    case "$STATUS" in
        healthy)
            HEALTHY=true
            break
            ;;
        unhealthy)
            log ERROR "容器健康检查失败"
            log ERROR "查看日志：docker logs frp-console"
            exit 1
            ;;
        *)
            # starting / 空，继续等
            printf "${DIM}.${RESET}"
            sleep 2
            WAITED=$((WAITED + 2))
            ;;
    esac
done

echo ""

if [ "$HEALTHY" = "true" ]; then
    log OK "容器健康检查通过"
else
    log WARN "等待超时（${MAX_WAIT}s），容器可能还在启动"
    log WARN "查看状态：docker ps"
    log WARN "查看日志：docker logs frp-console"
fi

echo ""

# ==================== 完成 ====================
# 从 .env 读端口
PORT=$(grep '^PORT=' .env | cut -d'=' -f2 | tr -d '[:space:]')
PORT=${PORT:-7600}

# 获取宿主机 IP
HOST_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$HOST_IP" ]; then
    HOST_IP="127.0.0.1"
fi

log OK "=== 部署完成 ==="
echo ""
echo "${GREEN}访问地址:${RESET}"
echo "  本机:   http://localhost:${PORT}"
echo "  局域网: http://${HOST_IP}:${PORT}"
echo ""
echo "${CYAN}登录信息:${RESET}"
echo "  用户名: admin"
echo "  密码:   见 .env 中的 ADMIN_PASSWORD"
echo ""
echo "${DIM}常用命令:${RESET}"
echo "  查看日志:   docker logs -f frp-console"
echo "  重启服务:   docker restart frp-console"
echo "  停止服务:   ${COMPOSE_CMD} down"
echo "  重新部署:   ./deploy.sh"
