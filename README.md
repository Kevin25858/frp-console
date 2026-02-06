# FRP Console

现代化的 FRPC 客户端管理控制台，提供 Web UI 来管理多个 FRPC 客户端。

## ✨ 特性

- **现代化 UI**：基于 React 18 + TypeScript + shadcn/ui 构建的美观界面
- **双主题支持**：支持亮色/暗色主题切换
- **实时监控**：实时查看客户端状态和日志
- **自动重启**：智能健康检查和自动恢复机制
- **告警通知**：邮件告警支持
- **模块化架构**：清晰的后端架构，易于维护和扩展
- **容器化部署**：支持 Docker 部署

## 🚀 快速开始

### 使用 Docker 部署（推荐）

#### 方式一：使用 Docker Compose（本地构建）

```bash
# 克隆项目
git clone <repository-url>
cd frp-console

# 配置环境变量（可选）
cp frp-console.conf.example frp-console.conf
# 编辑 frp-console.conf 设置你的配置

# 启动服务
docker-compose up -d

# 访问 http://localhost:7600
```

#### 方式二：使用 GitHub Container Registry（推荐）

```bash
# 拉取最新镜像
docker pull ghcr.io/kevin25858/frp-console:latest

# 运行容器
docker run -d --name frp-console -p 7600:7600 \
  -v /opt/frp-console/data:/app/data \
  -v /opt/frp-console/clients:/app/clients \
  -v /opt/frp-console/logs:/app/logs \
  -e ADMIN_PASSWORD=your_secure_password \
  -e SECRET_KEY=your_secret_key \
  --restart unless-stopped \
  ghcr.io/kevin25858/frp-console:latest

# 访问 http://localhost:7600
```

### 本地开发

#### 环境要求

- Python 3.12+
- Node.js 20+
- npm 或 yarn

#### 安装依赖

```bash
# 安装后端依赖
pip install -r requirements.txt

# 安装前端依赖
cd frontend
npm install
```

#### 配置

```bash
# 设置环境变量
export ADMIN_PASSWORD=your_password
export SECRET_KEY=your_secret_key
```

#### 运行

**开发模式：**

```bash
# Terminal 1: 启动后端
cd /opt/frp-console
python app/app.py

# Terminal 2: 启动前端开发服务器
cd frontend
npm run dev
```

**生产模式：**

```bash
# 构建前端
cd frontend
npm run build

# 启动后端
cd /opt/frp-console
export ADMIN_PASSWORD=your_password
python app/app.py
```

访问 http://localhost:7600

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

## � CI/CD

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
- **历史版本**: `ghcr.io/kevin25858/frp-console:<commit-sha>`

查看 [Actions](https://github.com/Kevin25858/frp-console/actions) 页面了解构建状态。

## �📝 API 文档

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