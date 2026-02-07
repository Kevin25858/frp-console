# FRP Console

一个 Web 端的 FRPC 客户端管理工具。不用手动改配置文件，在浏览器里就能管理多个 FRPC 客户端。

## 能做什么

- 在网页上配置 FRPC，不用记参数
- 一键启动、停止、重启客户端
- 实时看日志，不用登录服务器
- 客户端掉线自动邮件提醒

## 和传统方式对比

| 传统方式 | FRP Console |
|---------|-------------|
| 手动编辑 frpc.toml | 网页表单配置 |
| 逐个启动客户端 | 批量管理 |
| 看日志要登录服务器 | 浏览器直接看 |
| 掉线了不知道 | 自动发邮件 |

## 安装

### Docker 部署

```bash
# 拉取镜像
docker pull ghcr.io/kevin25858/frp-console:latest

# 运行（把 your_password 换成你的密码）
docker run -d --name frp-console -p 7600:7600 \
  -v /opt/frp-console/data:/app/data \
  -v /opt/frp-console/clients:/app/clients \
  -v /opt/frp-console/logs:/app/logs \
  -e ADMIN_PASSWORD=your_password \
  --restart unless-stopped \
  ghcr.io/kevin25858/frp-console:latest
```

然后访问 http://localhost:7600，用户名 admin，密码是你设置的。

### 更新

```bash
# 拉取最新镜像
docker pull ghcr.io/kevin25858/frp-console:latest

# 停止并删除旧容器
docker stop frp-console
docker rm frp-console

# 重新运行（数据不会丢失）
docker run -d --name frp-console -p 7600:7600 \
  -v /opt/frp-console/data:/app/data \
  -v /opt/frp-console/clients:/app/clients \
  -v /opt/frp-console/logs:/app/logs \
  -e ADMIN_PASSWORD=your_password \
  --restart unless-stopped \
  ghcr.io/kevin25858/frp-console:latest
```

注意：更新时加 `-e ADMIN_PASSWORD` 可以强制修改密码，不加则保留原来的密码。

## 功能

- 添加/编辑/删除客户端
- 启动/停止/重启客户端
- 实时查看日志
- 离线邮件告警
- 修改管理员密码

## 配置

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `PORT` | 服务端口 | 7600 |
| `ADMIN_USER` | 管理员用户名 | admin |
| `ADMIN_PASSWORD` | 管理员密码 | 随机生成 |
| `SECRET_KEY` | Flask 密钥 | 随机生成 |
| `SMTP_HOST` | SMTP 服务器 | smtp.qq.com |
| `SMTP_PORT` | SMTP 端口 | 587 |
| `SMTP_USER` | SMTP 用户 | - |
| `SMTP_PASSWORD` | SMTP 密码 | - |
| `ALERT_TO` | 告警接收邮箱 | - |

### 配置文件

配置文件在 `/opt/frp-console/frp-console.conf`：

```ini
PORT=7600
ADMIN_USER=admin
ADMIN_PASSWORD=ChangeMe123!@#
SECRET_KEY=ChangeThisSecretKeyInProduction
```

## 项目结构

```
frp-console/
├── app/                    # 后端
│   ├── api/               # API 路由
│   ├── services/          # 业务逻辑
│   ├── models/            # 数据模型
│   ├── utils/             # 工具函数
│   └── app.py             # 入口
├── frontend/              # 前端
│   └── src/
├── clients/               # 客户端配置
├── data/                  # 数据库
├── logs/                  # 日志
├── Dockerfile
└── requirements.txt
```

## 安全

- CSRF 保护
- 登录限制
- Session 管理
- 密码强度检查

## API

### 认证
- `POST /login` - 登录
- `GET /logout` - 登出

### 客户端
- `GET /api/clients` - 列表
- `POST /api/clients` - 创建
- `GET /api/clients/<id>` - 详情
- `PUT /api/clients/<id>` - 更新
- `DELETE /api/clients/<id>` - 删除
- `POST /api/clients/<id>/start` - 启动
- `POST /api/clients/<id>/stop` - 停止
- `POST /api/clients/<id>/restart` - 重启
- `GET /api/clients/<id>/logs` - 日志

## 参与贡献

1. Fork 项目
2. 创建分支 `git checkout -b feature/xxx`
3. 提交 `git commit -m 'Add xxx'`
4. 推送 `git push origin feature/xxx`
5. 提 Pull Request

## 许可证

MIT

## 感谢

- [FRP](https://github.com/fatedier/frp) - Fast Reverse Proxy
- [Flask](https://flask.palletsprojects.com/)
- [React](https://react.dev/)
