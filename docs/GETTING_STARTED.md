# FRP Console 入门指引

本面向第一次接触本项目的初学者。读完本文你能：
- 理解这个项目是做什么的
- 在本地把它跑起来
- 知道每个目录/文件的作用
- 知道代码里的注释和开发文档怎么对应

---

## 一、这个项目是做什么的

**FRP Console** 是 [frp](https://github.com/fatedier/frp) 的 Web 管理控制台。

frp 是一个内网穿透工具，能让外网访问你家里的服务器。但 frp 本身是命令行工具，要手写配置文件、手动启动。本项目给它套一层 Web 界面：

- 在网页上添加/编辑 frpc 配置
- 一键启动/停止 frpc 容器
- 查看运行日志
- 管理多个 frpc 客户端

**核心思路**：每个 frpc 客户端跑在独立的 Docker 容器里，Web 控制台通过 Docker SDK 管理这些容器。

---

## 二、技术栈速览

| 层 | 技术 | 作用 |
|---|---|---|
| 后端 | Flask (Python) | 提供 REST API 和网页 |
| 数据库 | SQLite | 存客户端配置（一个文件） |
| 容器管理 | Docker SDK | 启动/停止 frpc 容器 |
| 前端 | React + Vite | 单页应用（SPA） |
| 部署 | docker-compose | 一键启动整个系统 |

不需要精通这些技术就能读懂代码，但知道它们各自负责什么会有帮助。

---

## 三、第一次运行

### 3.1 准备环境

需要安装：
- Docker（用于跑 frpc 容器）
- Python 3.11+（后端运行时）
- Node.js 18+（前端构建用）

### 3.2 配置环境变量

复制 `.env.example` 为 `.env`，按需修改：

```bash
cp .env.example .env
```

关键字段：
- `ADMIN_PASSWORD`：管理员密码（不设则启动时随机生成并打印）
- `SECRET_KEY`：会话密钥（生产环境必须固定，否则重启要重新登录）
- `API_TOKEN`：frpc 拉取配置的令牌
- `DOCKER_GID`：宿主机 docker 组 ID（运行 `setup-host.sh` 会自动设置）

### 3.3 启动方式

**方式 A：Docker 部署（推荐生产环境）**

```bash
./setup-host.sh          # 配置宿主机 docker 组
docker-compose up -d --build
```

访问 http://localhost:7600

**方式 B：本地开发**

```bash
# 终端 1：跑后端
python app/app.py

# 终端 2：跑前端（修改代码自动刷新）
cd frontend
npm install
npm run dev
```

开发模式下前端跑在 5173 端口，会自动代理 API 请求到后端。

---

## 四、项目结构

```
frp-console/
├── app/                      # 后端 Python 代码
│   ├── app.py                # Flask 应用入口（创建 app、注册路由）
│   ├── config.py             # 配置管理（从环境变量读配置）
│   ├── api/routes/           # 路由层（URL -> 处理函数）
│   │   ├── auth.py           #   登录/登出/CSRF
│   │   └── clients.py        #   客户端增删改查
│   ├── services/             # 服务层（业务逻辑）
│   │   ├── auth_service.py   #   认证逻辑
│   │   ├── client_service.py #   客户端配置管理
│   │   └── process_service.py#   Docker 容器管理
│   ├── models/
│   │   └── database.py       # 数据库连接和建表
│   └── utils/                # 工具层
│       ├── logger.py         #   彩色日志
│       ├── password.py       #   密码哈希
│       ├── helpers.py        #   登录速率限制
│       └── validators.py     #   输入验证
├── frontend/                 # 前端 React 代码
│   ├── src/
│   │   ├── pages/            # 页面组件
│   │   ├── components/       # 通用组件
│   │   └── lib/api.ts        # API 调用封装
│   └── dist/                 # 前端构建产物（vite build 生成）
├── tests/                    # 后端测试
├── docs/                     # 文档（你正在看的目录）
├── docker-compose.yml        # 容器编排配置
├── Dockerfile                # 后端镜像构建脚本
└── requirements.txt          # Python 依赖
```

---

## 五、代码怎么读

本项目代码特意写成"初学者友好"风格，建议这样读：

### 5.1 阅读顺序

1. **先读 [app/app.py](../app/app.py)**：了解整个应用怎么搭起来
2. **再读 [app/config.py](../app/config.py)**：了解配置怎么管理
3. **然后读 [app/models/database.py](../app/models/database.py)**：了解数据存哪
4. **接着读 [app/services/](../app/services/)**：了解业务逻辑
5. **最后读 [app/api/routes/](../app/api/routes/)**：了解 API 接口

### 5.2 注释的约定

代码里的注释分两类：

**说明性注释**（在代码旁边）：
```python
# 用 ? 占位符而不是字符串拼接，防止 SQL 注入
db.execute('SELECT * FROM clients WHERE id = ?', (client_id,))
```

**教学性注释**（在文档字符串或块注释里）：
```python
"""
为什么用 ? 占位符而不是字符串拼接：
    如果用字符串拼接，攻击者可以在 client_id 里塞 "1 OR 1=1"，
    导致返回所有记录。? 占位符由数据库驱动安全转义。
"""
```

读到 `为什么...` / `什么是...` 这种注释时，停下来想想再继续。

### 5.3 和开发文档的对应

| 你想了解 | 看哪份文档 | 对应代码 |
|---|---|---|
| 项目整体架构 | [DEVELOPMENT.md](DEVELOPMENT.md) 第一章 | [app/app.py](../app/app.py) |
| 数据库设计 | [DEVELOPMENT.md](DEVELOPMENT.md) 第二章 | [app/models/database.py](../app/models/database.py) |
| API 接口列表 | [DEVELOPMENT.md](DEVELOPMENT.md) 第三章 | [app/api/routes/](../app/api/routes/) |
| 容器管理原理 | [DEVELOPMENT.md](DEVELOPMENT.md) 第四章 | [app/services/process_service.py](../app/services/process_service.py) |
| 安全设计 | [DEVELOPMENT.md](DEVELOPMENT.md) 第五章 | [app/services/auth_service.py](../app/services/auth_service.py)、[app/utils/password.py](../app/utils/password.py) |
| 如何写测试 | [DEVELOPMENT.md](DEVELOPMENT.md) 第六章 | [tests/](../tests/) |

---

## 六、常见概念扫盲

### 6.1 什么是 Blueprint（蓝图）

Flask 的模块化机制。把一组相关路由放在一起，整体注册到 app。

本项目有两个蓝图：
- `auth_bp`：认证相关（登录、登出、CSRF）
- `clients_bp`：客户端管理（增删改查、启动停止）

见 [app/app.py](../app/app.py) 第 100 行附近。

### 6.2 什么是 SPA

Single Page Application（单页应用）。

传统网站：每个 URL 对应一个 HTML 页面，点链接跳转到新页面。
SPA：只有一开始加载一个 HTML，之后所有跳转都在前端用 JS 完成。

本项目的 SPA 路由见 [app/app.py](../app/app.py) 的 `serve_spa` 函数：所有非 API 请求都返回 `index.html`，让前端 React Router 决定显示哪个页面。

### 6.3 什么是 CSRF

Cross-Site Request Forgery（跨站请求伪造）。

攻击场景：
1. 你登录了银行网站（cookie 还在）
2. 你又点开一个恶意网站
3. 恶意网站向银行发起转账请求，浏览器自动带上你的 cookie
4. 银行以为是你本人操作

防御方法：每次写操作要求带一个攻击者拿不到的随机 token。本项目实现在 [app/services/auth_service.py](../app/services/auth_service.py) 的 `get_csrf_token` / `verify_csrf_token`。

### 6.4 什么是 PBKDF2

密码哈希算法。和 MD5/SHA256 的区别是它故意很慢（迭代 10 万次），让暴力破解成本极高。

本项目用它存密码，见 [app/utils/password.py](../app/utils/password.py)。

### 6.5 什么是 WAL 模式

SQLite 的 Write-Ahead Logging 模式。让读操作不阻塞写操作，提高并发性能。

见 [app/models/database.py](../app/models/database.py) 的 `init_db` 函数。

---

## 七、遇到问题怎么办

### 7.1 启动失败

**问题**：`docker-compose up` 报权限错误
**原因**：当前用户不在 docker 组
**解决**：运行 `./setup-host.sh`，然后重新登录

**问题**：访问页面显示 404
**原因**：前端没构建
**解决**：在 `frontend/` 目录运行 `npm install && npm run build`

### 7.2 登录不上

**问题**：忘记管理员密码
**解决**：在 `.env` 里设 `ADMIN_PASSWORD=新密码`，重启容器

**问题**：登录提示"登录失败次数过多"
**原因**：被速率限制了（5 次失败锁 15 分钟）
**解决**：等 15 分钟，或重启容器（内存里的限制记录会清空）

### 7.3 客户端启动失败

**问题**：启动报"配置包含未修改的占位符"
**原因**：用了模板配置但没替换占位符
**解决**：编辑配置，把 `your-server-address` 等占位符换成实际值

**问题**：启动报"镜像拉取失败"
**原因**：网络问题拉不到 fatedier/frpc 镜像
**解决**：检查网络，或手动 `docker pull fatedier/frpc:v0.61.1`

### 7.4 看日志

容器日志：
```bash
docker logs FRPC-1      # 1 是客户端 ID
```

应用日志：直接看 docker-compose 输出：
```bash
docker-compose logs -f frp-console
```

---

## 八、下一步

读完本文后，建议：

1. 跟着 [DEVELOPMENT.md](DEVELOPMENT.md) 通读一遍架构
2. 在本地跑起来，点一点界面
3. 挑一个简单的测试文件读，比如 [tests/test_helpers.py](../tests/test_helpers.py)
4. 尝试改一个小功能（比如把速率限制从 5 次改成 3 次），跑测试看是否通过
