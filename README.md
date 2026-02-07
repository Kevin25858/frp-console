# FRP Console

> 一站式 FRPC 多客户端管理平台

告别繁琐的命令行配置，通过 Web UI 统一管理多个 FRPC 客户端，
实现可视化配置、批量管理、自动运维和实时监控。

## 🎯 为什么选择 FRP Console？

| 传统方式 | FRP Console |
|---------|-------------|
| 手动编辑 frpc.toml | 可视化表单配置 |
| 逐个启动客户端 | 一键批量管理 |
| 查看日志需登录服务器 | Web 端实时查看 |
| 故障无法及时感知 | 自动告警通知 |
| 配置分散难维护 | 集中式管理 |

## ✨ 核心特性

### 🖥️ 可视化配置管理
- 表单化配置，无需记忆参数
- 支持配置导入/导出
- 多客户端集中管理

### 🚀 自动化运维
- 客户端自动启动/重启
- 智能健康检查
- 故障自动恢复

### 📊 实时监控
- 在线状态监控
- 实时日志查看
- 流量统计概览

### 🔔 智能告警
- 离线告警
- 邮件通知
- 告警历史记录

## 🚀 快速开始

### 使用 Docker 部署（推荐）

```bash
# 拉取最新镜像
docker pull ghcr.io/kevin25858/frp-console:latest

# 运行容器（只需设置管理员密码）
docker run -d --name frp-console -p 7600:7600 \
  -v /opt/frp-console/data:/app/data \
  -v /opt/frp-console/clients:/app/clients \
  -v /opt/frp-console/logs:/app/logs \
  -e ADMIN_PASSWORD=your_secure_password \
  --restart unless-stopped \
  ghcr.io/kevin25858/frp-console:latest

# 访问 http://localhost:7600
```

## 📖 功能说明

### 客户端管理

- **添加客户端**：支持表单和配置粘贴两种方式
- **编辑客户端**：修改客户端配置信息
- **启动/停止/重启**：控制客户端运行状态
- **查看日志**：实时查看客户端运行日志
- **配置编辑**：直接编辑客户端配置文件
- **删除客户端**：安全删除客户端及其相关数据

### 仪表板

- 统计信息概览
- 实时客户端状态

### 告警系统

- 邮件告警通知
- 告警历史记录
- 告警类型过滤

### 设置

- 修改管理员密码
- 密码强度验证

## 🔧 配置

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `PORT` | 服务端口 | 7600 |
| `ADMIN_USER` | 管理员用户名 | admin |
| `ADMIN_PASSWORD` | 管理员密码 | admin123 |
| `SECRET_KEY` | Flask 密钥 | 随机生成 |
| `SMTP_HOST` | SMTP 服务器 | smtp.qq.com |
| `SMTP_PORT` | SMTP 端口 | 587 |
| `SMTP_USER` | SMTP 用户 | - |
| `SMTP_PASSWORD` | SMTP 密码 | - |
| `ALERT_TO` | 告警接收邮箱 | - |

### GitHub Container Registry

本项目使用 GitHub Container Registry (ghcr.io) 托管 Docker 镜像：

- **镜像地址**: `ghcr.io/kevin25858/frp-console:latest`
- **标签格式**: `ghcr.io/kevin25858/frp-console:<commit-sha>`

每次推送到 `main` 分支都会自动构建并推送最新镜像。

### 配置文件

配置文件位于 `/opt/frp-console/frp-console.conf`：

```ini
PORT=7600
ADMIN_USER=admin
ADMIN_PASSWORD=ChangeMe123!@#
SECRET_KEY=ChangeThisSecretKeyInProduction
```

## 🏗️ 项目结构

```
frp-console/
├── app/                    # 后端应用
│   ├── api/               # API 路由
│   │   └── routes/        # 路由模块
│   ├── services/          # 业务逻辑层
│   ├── models/            # 数据模型
│   ├── utils/             # 工具函数
│   ├── static/            # 静态文件
│   └── app.py             # 应用入口
├── frontend/              # 前端应用
│   ├── src/
│   │   ├── components/    # React 组件
│   │   ├── pages/         # 页面组件
│   │   ├── lib/           # 工具库
│   │   ├── contexts/      # React Context
│   │   └── types/         # TypeScript 类型
│   └── package.json
├── .github/workflows/     # GitHub Actions CI/CD
│   └── ci.yml             # CI/CD 配置
├── clients/               # 客户端配置文件
├── data/                  # 数据库文件
├── logs/                  # 日志文件
├── frpc/                  # FRPC 二进制文件
├── Dockerfile             # Docker 构建文件
├── docker-compose.yml     # Docker Compose 配置
└── requirements.txt       # Python 依赖
```

## 🔐 安全性

- CSRF 保护
- 登录速率限制
- Session 管理
- 密码复杂度验证（Zod）

## 🔄 CI/CD

本项目使用 GitHub Actions 实现自动化构建和部署：

### 工作流说明

| 任务 | 说明 | 触发条件 |
|------|------|----------|
| **Backend Tests** | Python 后端测试和代码检查 | Push / PR |
| **Frontend Tests** | 前端 TypeScript 检查和测试 | Push / PR |
| **Security Scan** | Trivy 安全漏洞扫描 | Push / PR |
| **Build** | Docker 镜像构建 | Push / PR |
| **Deploy** | 推送镜像到 ghcr.io | Push to main |

### 镜像地址

- **最新版本**: `ghcr.io/kevin25858/frp-console:latest`

查看 [Actions](https://github.com/Kevin25858/frp-console/actions) 页面了解构建状态。

## 📝 API 文档

### 认证

- `POST /login` - 用户登录
- `GET /logout` - 用户登出

### 客户端管理

- `GET /api/clients` - 获取客户端列表
- `POST /api/clients` - 创建客户端
- `GET /api/clients/<id>` - 获取客户端详情
- `PUT /api/clients/<id>` - 更新客户端
- `DELETE /api/clients/<id>` - 删除客户端
- `POST /api/clients/<id>/start` - 启动客户端
- `POST /api/clients/<id>/stop` - 停止客户端
- `POST /api/clients/<id>/restart` - 重启客户端
- `GET /api/clients/<id>/config` - 获取配置
- `PUT /api/clients/<id>/config` - 更新配置
- `GET /api/clients/<id>/logs` - 获取日志

### 告警

- `GET /api/alerts` - 获取告警列表

### 管理员

- `POST /api/change-password` - 修改密码

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [FRP](https://github.com/fatedier/frp) - Fast Reverse Proxy
- [Flask](https://flask.palletsprojects.com/) - Python Web 框架
- [React](https://react.dev/) - React 框架
- [shadcn/ui](https://ui.shadcn.com/) - UI 组件库
