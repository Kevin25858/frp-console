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

- **客户端配置管理** - 创建、编辑、删除 frpc TOML 配置
- **配置编辑器** - 内置 TOML 编辑器，支持语法高亮和格式验证
- **配置导出 API** - frpc 通过 Bearer Token 拉取配置
- **批量操作** - 批量启用/禁用客户端配置
- **单用户认证** - 管理员密码登录，支持修改密码
- **Docker 部署** - 一键容器化部署

## 系统架构

```
服务器
├── Docker 容器 (Web 管理端)
│   └── FRP Console (端口 7600)
│       ├── Web 管理界面 (React SPA)
│       ├── RESTful API (Flask)
│       └── 配置存储 (SQLite)
│
└── 宿主机 systemd 服务
    └── frpc-{id}.service (每个客户端独立进程)
```

Web 端只管理配置，frpc 进程在宿主机独立运行。配置文件路径：`/etc/frp-client/frpc-{id}.toml`

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
# 初始化宿主机环境（systemd 模板、D-Bus 策略、配置目录权限）
sudo bash setup-host.sh

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
| `PORT` | 服务端口 | 否 | 7600 |
| `TZ` | 时区 | 否 | Asia/Shanghai |
| `FORCE_HTTPS` | 强制 HTTPS | 否 | false |

**安全提示**：
- `ADMIN_PASSWORD`、`SECRET_KEY` 和 `API_TOKEN` 必须通过 `.env` 文件或环境变量设置
- 建议使用 `openssl rand -hex 32` 生成 `SECRET_KEY`
- 建议使用 `openssl rand -hex 16` 生成 `API_TOKEN`

## 使用指南

### 创建客户端

1. 登录 Web 控制台
2. 进入「客户端管理」页面
3. 点击「添加客户端」
4. 粘贴或编辑 TOML 格式的 frpc 配置
5. 保存配置

### 进程管理

每个客户端支持独立的启动/停止/重启操作。宿主机需要先运行 `setup-host.sh` 初始化环境。

工作原理：容器内通过 D-Bus 调用宿主机的 systemd 来管理 `frpc-console@{id}.service` 模板单元。配置文件会自动同步到 `/etc/frp-client/frpc-{id}.toml`。

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
| DELETE | `/api/clients/{id}` | 删除客户端 |
| GET | `/api/clients/{id}/config` | 获取客户端配置 |
| PUT | `/api/clients/{id}/config` | 更新客户端配置 |
| GET | `/api/clients/{id}/config/export` | 导出配置（Bearer Token 认证） |
| POST | `/api/clients/batch-enable` | 批量启用/禁用 |
| POST | `/api/clients/{id}/start` | 启动客户端进程 |
| POST | `/api/clients/{id}/stop` | 停止客户端进程 |
| POST | `/api/clients/{id}/restart` | 重启客户端进程 |
| GET | `/api/clients/{id}/status` | 获取进程状态 |
| GET | `/api/clients/{id}/logs` | 获取进程日志 |

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
│   │   └── client_service.py  # 客户端服务
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
