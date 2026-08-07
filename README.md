<div align="center">

<img src="https://raw.githubusercontent.com/Kevin25858/frp-console/main/assets/logo.svg" width="120" height="120" alt="FRP Console Logo">

# FRP Console

**轻量级 FRP 客户端配置管理工具**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-20+-green.svg)](https://nodejs.org/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](https://www.docker.com/)

</div>

---

FRP Console 是一个轻量级的 FRP (Fast Reverse Proxy) 客户端配置管理工具，通过 Web 界面集中管理多个 frpc 实例的 TOML 配置文件。

## 核心功能

- **客户端配置管理** - 创建（粘贴配置或表单生成）、编辑、删除 frpc TOML 配置
- **配置编辑器** - 内置 TOML 编辑器，支持语法高亮和格式验证
- **容器生命周期管理** - 通过 Docker SDK 启动/停止/重启 frpc 容器
- **版本管理** - 自动获取 frp 最新版本，或按客户端指定版本
- **占位符校验** - 启动前检查配置是否含未修改的占位符
- **配置备份** - 覆盖前自动备份原配置文件
- **配置导出 API** - frpc 通过 Bearer Token 拉取配置
- **批量操作** - 批量启用/禁用所有客户端
- **单用户认证** - 管理员密码登录，支持修改密码
- **Docker 部署** - 一键容器化部署

## 系统架构

```
宿主机
├── /var/run/docker.sock                      # 挂载进 Web 容器，用于管理 frpc 容器
├── /opt/frpc/                               # 配置源目录
│   ├── frpc-1.toml                           # 由 Web 容器写入，权限 600
│   └── frpc-1.toml.backup.<ts>               # 覆盖前自动备份
└── Docker 引擎
    ├── frp-console 容器                      # Web 应用（Flask + React SPA），非 root
    │   └── 通过 /var/run/docker.sock 管理下方容器
    └── FRPC-{id} 容器                        # 每个客户端一个，fatedier/frpc:<ver>
        ├── --network host --restart always
        ├── -v /opt/frpc/frpc-{id}.toml:/etc/frp/frpc.toml:ro
        └── 健康检查: pgrep frpc
```

frpc 以 `fatedier/frpc` 容器方式运行，Web 控制台通过 Docker SDK（挂载宿主机 `docker.sock`）管理容器生命周期。配置文件路径：`/opt/frpc/frpc-{id}.toml`

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.12+ / Flask / SQLite |
| 前端 | React 18 / TypeScript / Vite |
| UI 框架 | Tailwind CSS / shadcn/ui |
| 部署 | Docker |

## 快速开始

### Docker 部署（推荐）

```bash
# 创建目录
mkdir -p /opt/frp-console && cd /opt/frp-console

# 克隆仓库
git clone https://github.com/Kevin25858/frp-console.git .

# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件
nano .env
```

`.env` 文件示例：

```bash
# 必需配置
ADMIN_PASSWORD=your_strong_password
SECRET_KEY=$(openssl rand -hex 32)
API_TOKEN=$(openssl rand -hex 16)

# 基础配置
PORT=7600
TZ=Asia/Shanghai
```

```bash
# 初始化宿主机环境（创建配置目录、获取 Docker 组 GID）
sudo bash setup-host.sh

# 将输出的 DOCKER_GID 写入 .env
# 例如: DOCKER_GID=998

# 启动服务
docker compose up -d --build
```

### 环境变量

| 变量名 | 说明 | 必需 | 默认值 |
|--------|------|------|--------|
| `ADMIN_USER` | 管理员用户名 | 否 | admin |
| `ADMIN_PASSWORD` | 管理员密码 | **是** | 无 |
| `SECRET_KEY` | Flask 会话密钥 | **是** | 无 |
| `API_TOKEN` | 配置导出 API 认证令牌 | **是** | 无 |
| `DOCKER_GID` | 宿主机 docker 组 GID | **是** | 999 |
| `PORT` | 服务端口 | 否 | 7600 |
| `TZ` | 时区 | 否 | Asia/Shanghai |
| `FORCE_HTTPS` | 强制 HTTPS | 否 | false |

**安全提示**：
- `ADMIN_PASSWORD`、`SECRET_KEY` 和 `API_TOKEN` 必须通过 `.env` 文件或环境变量设置
- 建议使用 `openssl rand -hex 32` 生成 `SECRET_KEY`
- 建议使用 `openssl rand -hex 16` 生成 `API_TOKEN`
- `DOCKER_GID` 通过 `stat -c '%g' /var/run/docker.sock` 获取，或运行 `setup-host.sh` 自动检测

## 使用指南

### 创建客户端

1. 登录 Web 控制台
2. 进入「客户端管理」页面
3. 点击「添加客户端」
4. 选择模式：
   - **粘贴配置** - 直接粘贴现有 frpc TOML 配置
   - **表单生成** - 填写服务器地址、端口、代理信息，自动生成 TOML
5. 可选指定 frp 版本（留空则自动取最新）
6. 保存配置

### 容器管理

每个客户端支持独立的启动/停止/重启操作。点击「启动」时，Web 控制台会：

1. 将配置写入 `/opt/frpc/frpc-{id}.toml`（覆盖前自动备份）
2. 校验配置是否含未修改的占位符（如 `your-server-address`），有则拒绝启动
3. 拉取 `fatedier/frpc:<version>` 镜像（版本留空时自动从 GitHub 获取最新）
4. 创建并启动容器 `FRPC-{id}`（`--network host --restart always`，配置只读挂载）
5. 回写解析后的镜像版本到数据库

容器状态（running/stopped/error）实时显示在列表中。「查看日志」读取容器 stdout 日志。

### 配置导出

frpc 可通过 API 拉取配置：

```bash
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
     http://your-server:7600/api/clients/1/config/export
```

## API 文档

### 认证

```http
POST /login
Content-Type: application/json

{"username": "admin", "password": "your_password"}
```

### 客户端管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/clients` | 获取客户端列表 |
| POST | `/api/clients` | 创建客户端 |
| GET | `/api/clients/{id}` | 获取客户端详情 |
| PUT | `/api/clients/{id}` | 更新客户端信息 |
| DELETE | `/api/clients/{id}` | 删除客户端（同时移除容器与配置文件） |
| GET | `/api/clients/{id}/config` | 获取客户端配置 |
| PUT | `/api/clients/{id}/config` | 更新客户端配置 |
| GET | `/api/configs/{id}/export` | 导出配置（Bearer Token 认证） |
| POST | `/api/clients/batch-enable` | 批量启用/禁用所有客户端 |
| POST | `/api/clients/{id}/start` | 启动客户端容器 |
| POST | `/api/clients/{id}/stop` | 停止客户端容器 |
| POST | `/api/clients/{id}/restart` | 重启客户端容器 |
| GET | `/api/clients/{id}/status` | 获取容器实时状态 |
| GET | `/api/clients/{id}/logs` | 获取容器日志 |
| POST | `/api/clients/{id}/clear-logs` | 清空容器日志（recreate 容器） |

### 其他

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/csrf-token` | 获取 CSRF token |
| GET | `/api/me` | 获取当前用户信息 |
| POST | `/api/change-password` | 修改密码 |

## 项目结构

```
frp-console/
├── app/                        # 后端应用
│   ├── api/routes/            # API 路由
│   │   ├── auth.py            # 认证路由
│   │   └── clients.py         # 客户端路由
│   ├── services/              # 业务逻辑层
│   │   ├── auth_service.py    # 认证服务
│   │   ├── client_service.py  # 客户端 CRUD 服务
│   │   └── process_service.py # Docker 容器管理服务
│   ├── models/                # 数据模型
│   ├── utils/                 # 工具函数
│   ├── config.py              # 配置管理
│   └── app.py                 # 应用入口
├── frontend/                   # 前端应用
│   └── src/
│       ├── components/        # React 组件
│       ├── pages/             # 页面组件
│       ├── contexts/          # React Context
│       ├── lib/               # 工具库
│       └── types/             # TypeScript 类型
├── tests/                      # 测试文件
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 安全特性

| 特性 | 说明 |
|------|------|
| **密码哈希** | PBKDF2-HMAC-SHA256 (100,000 次迭代) |
| **登录保护** | 速率限制 (5 次 / 15 分钟) |
| **CSRF 防护** | 所有表单和 API 端点保护 |
| **Session 安全** | HttpOnly, SameSite |
| **Docker 安全** | 非 root 用户运行 |
| **SQL 注入防护** | 参数化查询 |

## 许可证

MIT License

## 致谢

- [FRP](https://github.com/fatedier/frp) - Fast Reverse Proxy
- [Flask](https://flask.palletsprojects.com/)
- [React](https://react.dev/)
- [shadcn/ui](https://ui.shadcn.com/)
