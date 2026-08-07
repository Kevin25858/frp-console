#!/bin/bash
# FRP Console - 宿主机初始化脚本
# 在宿主机上运行此脚本，为 Docker 容器化管理做准备
# 提示：全新环境推荐直接运行 install.sh（自动装 Docker、建目录、生成 .env 并启动）
set -e

# 若非 root，用 sudo
SUDO=""
[ "$(id -u)" -ne 0 ] && SUDO="sudo"

echo "=== FRP Console 宿主机设置 ==="

# 1. 创建配置目录并设置权限
echo "[1/2] 创建配置目录..."
$SUDO mkdir -p /opt/frpc
# appuser 的 UID 是 1000（Dockerfile 中创建）
$SUDO chown -R 1000:1000 /opt/frpc
$SUDO chmod 755 /opt/frpc

# 2. 获取 Docker 组 GID
echo "[2/2] 获取 Docker 组 GID..."
DOCKER_GID=$(stat -c '%g' /var/run/docker.sock 2>/dev/null || echo "999")
echo ""
echo "=== 设置完成 ==="
echo "宿主机 docker.sock 的 GID 为: ${DOCKER_GID}"
echo "请将此值写入 .env 文件中的 DOCKER_GID，例如:"
echo "  DOCKER_GID=${DOCKER_GID}"
echo ""
echo "然后执行: docker compose up -d --build"
echo "或全新环境直接运行: bash install.sh"
