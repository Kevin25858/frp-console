# ⚠️ 项目维护通知

**本项目已停止对外开放，不再接受新的用户使用。**

---

# FRP Console

一个 Web 端的 FRP 配置管理工具。Web 管理界面和 frpc 在同一台服务器上运行，frpc 通过 systemd 独立运行，不受 Docker 影响。

![仪表板](https://github.com/Kevin25858/frp-console/blob/main/docs/screenshots/dashboard.png?raw=true)

## 能做什么

- 在网页上配置 FRPC，不用记参数
- Web 端管理配置，frpc 独立运行
- Docker 重启不影响 frpc
- 一键安装部署

## 架构说明

```
同一台服务器
├─ Docker 容器 (Web 管理端)
│   └─ FRP Console (端口 7600)
│       ├─ 配置管理界面
│       ├─ 控制 frpc 服务（调用 systemctl）
│       └─ 提供配置 API
│
└─ 宿主机 systemd 服务
    ├─ frpc.service (实际运行 frpc)
    └─ frpc-sync.timer (每分钟同步配置)
```

**核心特点**：
- Web 端只管理配置，不直接运行 frpc
- frpc 通过 systemd 独立运行（在宿主机上，不在 Docker 内）
- 配置自动同步（每分钟检查一次）
- Docker 容器重启/删除不影响 frpc

## 一键安装

```bash
curl -fsSL https://raw.githubusercontent.com/Kevin25858/frp-console/main/install.sh | sudo bash
```

或先下载再执行：

```bash
wget https://raw.githubusercontent.com/Kevin25858/frp-console/main/install.sh
chmod +x install.sh
sudo ./install.sh
```

安装过程会提示输入：
- 管理员密码
- API Token
- 服务端口（默认 7600）

安装完成后访问：`http://服务器IP:7600`

## 手动安装

### 1. 部署 Web 管理端

```bash
# 创建目录
mkdir -p /opt/frp-console
cd /opt/frp-console

# 创建 docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  frp-console:
    image: ghcr.io/kevin25858/frp-console:latest
    container_name: frp-console
    restart: unless-stopped
    ports:
      - "7600:7600"
    environment:
      - PORT=7600
      - ADMIN_PASSWORD=your_password
      - SECRET_KEY=your_secret_key
      - API_TOKEN=your_api_token
    volumes:
      - ./data:/app/data
EOF

# 启动
docker-compose up -d
```

### 2. 部署 frpc（在同一台服务器）

```bash
# 下载 frpc
wget https://github.com/fatedier/frp/releases/download/v0.52.3/frp_0.52.3_linux_amd64.tar.gz
tar -xzf frp_0.52.3_linux_amd64.tar.gz
cp frp_0.52.3_linux_amd64/frpc /usr/local/bin/
chmod +x /usr/local/bin/frpc

# 创建配置目录
mkdir -p /etc/frp-client

# 创建 systemd 服务
cat > /etc/systemd/system/frpc.service << 'EOF'
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

# 创建配置同步脚本
cat > /usr/local/bin/frpc-sync.sh << 'SCRIPT'
#!/bin/bash
CONFIG_FILE="/etc/frp-client/frpc.toml"
TEMP_FILE="/etc/frp-client/frpc.toml.tmp"
LOG_FILE="/var/log/frpc-sync.log"
API_TOKEN="your_api_token"
PORT="7600"

# 拉取配置
fetch_config() {
    if ! curl -s -H "Authorization: Bearer $API_TOKEN" \
         "http://localhost:$PORT/api/configs/1/export" > "$TEMP_FILE" 2>/dev/null; then
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

# 创建定时任务
cat > /etc/systemd/system/frpc-sync.service << 'EOF'
[Unit]
Description=FRP Config Sync
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/frpc-sync.sh
EOF

cat > /etc/systemd/system/frpc-sync.timer << 'EOF'
[Unit]
Description=FRP Config Sync Timer

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min

[Install]
WantedBy=timers.target
EOF

# 启动服务
systemctl daemon-reload
systemctl enable frpc
systemctl enable frpc-sync.timer
systemctl start frpc-sync.timer

# 首次拉取配置
/usr/local/bin/frpc-sync.sh
```

## 使用流程

### 1. 创建客户端配置

1. 登录 Web 控制台（http://服务器IP:7600）
2. 点击"添加客户端"
3. 填写配置信息（服务器地址、端口、Token 等）
4. 保存配置

### 2. 管理 frpc 服务

在 Web 界面点击按钮：
- **启动** - 启动 frpc 服务
- **停止** - 停止 frpc 服务
- **重启** - 重启 frpc 服务

或在命令行管理：
```bash
# 查看状态
systemctl status frpc

# 启动
systemctl start frpc

# 停止
systemctl stop frpc

# 重启
systemctl restart frpc

# 查看日志
journalctl -u frpc -f
```

### 3. 配置同步

- 在 Web 端修改配置
- 配置会自动同步到 frpc（每分钟检查一次）
- 如有变化，frpc 会自动重启

## 更新

### Web 端更新

```bash
cd /opt/frp-console
docker-compose pull
docker-compose up -d
```

**注意**：Web 端更新不会影响正在运行的 frpc！

### frpc 更新

```bash
# 停止 frpc
systemctl stop frpc

# 下载新版本
wget https://github.com/fatedier/frp/releases/download/v0.52.3/frp_0.52.3_linux_amd64.tar.gz
tar -xzf frp_0.52.3_linux_amd64.tar.gz
cp frp_0.52.3_linux_amd64/frpc /usr/local/bin/frpc
chmod +x /usr/local/bin/frpc

# 启动 frpc
systemctl start frpc
```

## 环境变量说明

| 变量名 | 说明 | 必需 |
|--------|------|------|
| `ADMIN_PASSWORD` | 管理员密码 | 是 |
| `SECRET_KEY` | Flask 密钥 | 是 |
| `API_TOKEN` | frpc 拉取配置的 Token | 是 |
| `PORT` | 服务端口 | 否（默认7600） |

## API

### 认证
- `POST /login` - 登录（Web 界面）

### 客户端管理
- `GET /api/clients` - 列表
- `POST /api/clients` - 创建
- `GET /api/clients/<id>` - 详情
- `PUT /api/clients/<id>` - 更新
- `DELETE /api/clients/<id>` - 删除
- `GET /api/clients/<id>/config` - 获取配置
- `PUT /api/clients/<id>/config` - 更新配置

### 服务控制
- `POST /api/service/start` - 启动 frpc
- `POST /api/service/stop` - 停止 frpc
- `POST /api/service/restart` - 重启 frpc
- `GET /api/service/status` - 获取 frpc 状态

### 配置导出（供 frpc 使用）
- `GET /api/configs/<id>/export` - 导出配置（需要 Bearer Token）

```bash
curl -H "Authorization: Bearer <API_TOKEN>" \
     http://localhost:7600/api/configs/1/export
```

## 安全

- 所有 API 都需要认证
- Web 界面使用 Session 认证
- 配置导出使用 Token 认证
- 支持 HTTPS（通过反向代理）

## 项目结构

```
frp-console/
├── app/                    # 后端
│   ├── api/               # API 路由
│   ├── services/          # 业务逻辑
│   ├── models/            # 数据模型
│   └── app.py             # 入口
├── frontend/              # 前端
│   └── src/
├── scripts/               # 部署脚本
│   └── install-frpc.sh    # frpc 安装脚本（备用）
├── install.sh             # 一键安装脚本
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 许可证

MIT

## 感谢

- [FRP](https://github.com/fatedier/frp) - Fast Reverse Proxy
- [Flask](https://flask.palletsprojects.com/)
- [React](https://react.dev/)
