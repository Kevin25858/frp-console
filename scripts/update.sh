#!/bin/bash
# FRP Console 更新脚本
# 用于更新 Web 管理端到最新版本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
log() { echo -e "${BLUE}[LOG]${NC} $1"; }

# 显示帮助信息
show_help() {
    cat << EOF
FRP Console 更新脚本

用法: $0 [选项]

选项:
    -h, --help          显示帮助信息
    -n, --no-backup     更新前不备份数据
    -y, --yes           自动确认，不提示
    -f, --full          完整更新（包含镜像清理）

示例:
    $0                  # 标准更新（推荐）
    $0 --no-backup      # 更新但不备份
    $0 --full           # 完整更新并清理旧镜像

EOF
}

# 默认配置
BACKUP=true
AUTO_CONFIRM=false
FULL_UPDATE=false

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -n|--no-backup)
            BACKUP=false
            shift
            ;;
        -y|--yes)
            AUTO_CONFIRM=true
            shift
            ;;
        -f|--full)
            FULL_UPDATE=true
            shift
            ;;
        *)
            error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 检测安装目录
if [[ -f "docker-compose.yml" ]]; then
    INSTALL_DIR="$(pwd)"
elif [[ -d "/opt/frp-console" && -f "/opt/frp-console/docker-compose.yml" ]]; then
    INSTALL_DIR="/opt/frp-console"
else
    error "未找到 docker-compose.yml，请确保在 FRP Console 安装目录运行此脚本"
    exit 1
fi

cd "$INSTALL_DIR"
info "检测到安装目录: $INSTALL_DIR"

# 检测 docker compose 命令
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    error "未找到 docker-compose 或 docker compose 命令"
    exit 1
fi
info "使用命令: $DOCKER_COMPOSE"

# 检查容器状态
info "检查当前容器状态..."
if $DOCKER_COMPOSE ps | grep -q "frp-console"; then
    CONTAINER_RUNNING=true
    info "FRP Console 容器正在运行"
else
    CONTAINER_RUNNING=false
    warn "FRP Console 容器未运行"
fi

# 确认更新
if [[ "$AUTO_CONFIRM" == false ]]; then
    echo ""
    echo "========================================"
    echo "  FRP Console 更新"
    echo "========================================"
    echo ""
    echo "安装目录: $INSTALL_DIR"
    echo "数据备份: $([[ $BACKUP == true ]] && echo '是' || echo '否')"
    echo "完整更新: $([[ $FULL_UPDATE == true ]] && echo '是' || echo '否')"
    echo ""
    read -p "确认更新? [Y/n]: " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]] && [[ -n $confirm ]]; then
        info "已取消更新"
        exit 0
    fi
fi

# 备份数据
if [[ "$BACKUP" == true ]]; then
    BACKUP_DIR="backup/$(date +%Y%m%d_%H%M%S)"
    info "创建数据备份: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"

    if [[ -d "data" ]]; then
        cp -r data "$BACKUP_DIR/"
        log "已备份 data 目录"
    fi

    if [[ -d "logs" ]]; then
        cp -r logs "$BACKUP_DIR/"
        log "已备份 logs 目录"
    fi

    if [[ -f "docker-compose.yml" ]]; then
        cp docker-compose.yml "$BACKUP_DIR/"
        log "已备份 docker-compose.yml"
    fi

    info "备份完成，存储在: $INSTALL_DIR/$BACKUP_DIR"
fi

# 拉取最新镜像
echo ""
info "拉取最新镜像..."
$DOCKER_COMPOSE pull

# 重启容器
echo ""
info "重启容器..."
$DOCKER_COMPOSE up -d

# 等待服务启动
echo ""
info "等待服务启动..."
for i in {1..30}; do
    if curl -s http://localhost:7600/login > /dev/null 2>&1; then
        info "服务启动成功！"
        break
    fi
    sleep 1
    if [[ $i -eq 30 ]]; then
        warn "服务启动超时，请手动检查状态"
    fi
done

# 完整更新：清理旧镜像
if [[ "$FULL_UPDATE" == true ]]; then
    echo ""
    info "清理旧镜像..."
    docker image prune -f || true
fi

# 显示更新结果
echo ""
echo "========================================"
echo "  更新完成！"
echo "========================================"
echo ""

# 显示容器状态
$DOCKER_COMPOSE ps

echo ""
info "FRP Console 已更新到最新版本"
echo ""
echo "访问地址: http://$(hostname -I | awk '{print $1}'):7600"
echo ""

if [[ "$BACKUP" == true ]]; then
    echo "数据备份位置: $INSTALL_DIR/$BACKUP_DIR"
    echo ""
fi

echo "常用命令:"
echo "  查看日志: $DOCKER_COMPOSE logs -f"
echo "  查看状态: $DOCKER_COMPOSE ps"
echo "  重启服务: $DOCKER_COMPOSE restart"
echo ""
