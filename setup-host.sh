#!/bin/bash
# FRP Console - 宿主机初始化脚本
# 在宿主机上运行此脚本，为 Docker 容器内的进程管理做准备
set -e

echo "=== FRP Console 宿主机设置 ==="

# 1. 创建 systemd 模板单元
echo "[1/5] 创建 systemd 模板单元..."
cat > /etc/systemd/system/frpc-console@.service << 'EOF'
[Unit]
Description=FRP Client (Console managed) - %i
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/frpc -c /etc/frp-client/frpc-%i.toml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 2. 创建 D-Bus 策略允许容器内 appuser (UID 999) 调用 systemd
echo "[2/5] 配置 D-Bus 策略..."
mkdir -p /etc/dbus-1/system.d
cat > /etc/dbus-1/system.d/frp-console.conf << 'EOF'
<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-BUS Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <policy user="999">
    <allow send_destination="org.freedesktop.systemd1"/>
    <allow send_interface="org.freedesktop.systemd1.Manager"/>
  </policy>
</busconfig>
EOF
systemctl reload dbus 2>/dev/null || true

# 3. 配置 sudoers（容器内 appuser 通过 sudo busctl 调用 systemd）
echo "[3/5] 配置 sudoers..."
cat > /etc/sudoers.d/frp-console << 'EOF'
Defaults:appuser !use_pty
appuser ALL=(root) NOPASSWD: /usr/bin/systemctl start frpc-console@*
appuser ALL=(root) NOPASSWD: /usr/bin/systemctl stop frpc-console@*
appuser ALL=(root) NOPASSWD: /usr/bin/systemctl restart frpc-console@*
appuser ALL=(root) NOPASSWD: /usr/bin/systemctl is-active frpc-console@*
appuser ALL=(root) NOPASSWD: /usr/bin/systemctl status frpc-console@*
appuser ALL=(root) NOPASSWD: /usr/bin/systemctl enable frpc-console@*
appuser ALL=(root) NOPASSWD: /usr/bin/systemctl disable frpc-console@*
appuser ALL=(root) NOPASSWD: /usr/bin/busctl *
appuser ALL=(root) NOPASSWD: /usr/bin/journalctl --rotate -u frpc-console@*
appuser ALL=(root) NOPASSWD: /usr/bin/journalctl --vacuum-time=1s -u frpc-console@*
EOF
chmod 440 /etc/sudoers.d/frp-console

# 4. 创建配置目录并设置权限
echo "[4/5] 配置目录权限..."
mkdir -p /etc/frp-client
# appuser 的 UID 是 999（Dockerfile 中创建）
chown -R 999:999 /etc/frp-client
chmod 755 /etc/frp-client

# 5. 重新加载 systemd
echo "[5/5] 重新加载 systemd..."
systemctl daemon-reload

echo ""
echo "=== 设置完成 ==="
echo "现在可以运行: docker compose up -d --build"
