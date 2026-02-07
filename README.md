# FRP Console

一个 Web 端的 FRP 配置管理工具。纯管理界面，不运行 frpc，frpc 在独立的服务器上运行。

![仪表板](https://github.com/Kevin25858/frp-console/blob/main/docs/screenshots/dashboard.png?raw=true)

## 能做什么

- 在网页上配置 FRPC，不用记参数
- 配置自动同步到远程 frpc 客户端
- 纯 Web 管理，frpc 独立运行，互不影响
- 多服务器统一管理

## 架构说明

```
┌─────────────────────────┐         ┌─────────────────────────┐
│   Docker: Web管理端      │         │   服务器A/B/C/...        │
│  ┌─────────────────┐    │         │  ┌─────────────────┐    │
│  │  FRP Console    │    │         │  │  systemd        │    │
│  │  - 配置管理界面  │◄───┼──API────┼──┤  ├─ config-sync  │    │
│  │  - 配置存储      │    │  拉配置  │  │  └─ frpc        │    │
│  │  - 端口7600      │    │         │  └─────────────────┘    │
│  └─────────────────┘    │         │                         │
│                         │         │  Docker重启/删除不影响    │
│  可以任意重启/更新       │         │  frpc 持续运行           │
└─────────────────────────┘         └─────────────────────────┘
```

**核心特点**：
- Web 端只管理配置，不运行 frpc
- frpc 在目标服务器上独立运行（systemd 管理）
- 配置自动同步（每分钟检查一次）
- Docker 容器重启/删除不影响 frpc

## 安装

### 1. 部署 Web 管理端

#### Docker Compose 部署

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

然后访问 http://localhost:7600，用户名 admin，密码是你设置的。

#### 环境变量说明

| 变量名 | 说明 | 必需 |
|--------|------|------|
| `ADMIN_PASSWORD` | 管理员密码 | 是 |
| `SECRET_KEY` | Flask 密钥 | 是 |
| `API_TOKEN` | frpc 拉取配置的 Token | 是 |
| `PORT` | 服务端口 | 否（默认7600） |

### 2. 在目标服务器上部署 frpc

在需要运行 frpc 的服务器上执行：

```bash
# 下载安装脚本
wget https://raw.githubusercontent.com/Kevin25858/frp-console/main/scripts/install-frpc.sh
chmod +x install-frpc.sh

# 安装 frpc（替换为你的实际参数）
./install-frpc.sh \
  -u http://web-server-ip:7600 \
  -i 1 \
  -t your_api_token
```

参数说明：
- `-u`: Web 控制台地址
- `-i`: 客户端 ID（在 Web 控制台创建的客户端 ID）
- `-t`: API Token（和 Web 端设置的相同）

安装完成后，frpc 会：n1. 立即从 Web 控制台拉取配置
2. 每分钟自动检查配置是否有更新
3. 如有更新，自动重启 frpc

## 使用流程

### 1. 创建客户端配置

1. 登录 Web 控制台
2. 点击"添加客户端"
3. 填写配置信息（服务器地址、端口、Token 等）
4. 保存后记住客户端 ID

### 2. 在目标服务器部署

```bash
./install-frpc.sh -u http://web-ip:7600 -i <客户端ID> -t <API_TOKEN>
```

### 3. 管理配置

- 在 Web 端修改配置
- frpc 会自动同步（每分钟检查一次）
- 无需手动重启 frpc

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
# 在 frpc 所在服务器执行
systemctl stop frpc-client
./install-frpc.sh -u http://web-ip:7600 -i <客户端ID> -t <API_TOKEN>
```

## 多服务器管理

可以在多台服务器上部署 frpc，都连接到同一个 Web 控制台：

```bash
# 服务器 A
./install-frpc.sh -u http://web-ip:7600 -i 1 -t token

# 服务器 B
./install-frpc.sh -u http://web-ip:7600 -i 2 -t token

# 服务器 C
./install-frpc.sh -u http://web-ip:7600 -i 3 -t token
```

每台服务器独立运行，互不影响。

## 手动管理 frpc

```bash
# 查看状态
systemctl status frpc-client

# 启动
systemctl start frpc-client

# 停止
systemctl stop frpc-client

# 重启
systemctl restart frpc-client

# 查看日志
journalctl -u frpc-client -f

# 查看配置同步日志
cat /etc/frp-client/sync.log
```

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

### 配置导出（供 frpc 使用）
- `GET /api/configs/<id>/export` - 导出配置（需要 Bearer Token）

```bash
curl -H "Authorization: Bearer <API_TOKEN>" \
     http://web-ip:7600/api/configs/1/export
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
│   └── install-frpc.sh    # frpc 安装脚本
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
