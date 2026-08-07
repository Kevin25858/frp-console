# FRP Console 开发文档

本文件是项目的"说明书"，和代码里的注释相互呼应。
每章都会指出对应的代码文件，建议对照源码阅读。

---

## 目录

1. [整体架构](#一整体架构)
2. [数据库设计](#二数据库设计)
3. [API 接口](#三api-接口)
4. [容器管理原理](#四容器管理原理)
5. [安全设计](#五安全设计)
6. [测试体系](#六测试体系)
7. [开发流程](#七开发流程)
8. [扩展指南](#八扩展指南)

---

## 一、整体架构

### 1.1 分层架构

本项目采用经典的四层架构：

```
┌──────────────────────────────────────────┐
│  前端 (React SPA)                        │
│  - 页面渲染、用户交互                     │
│  - 通过 fetch 调用后端 API                │
└────────────────┬─────────────────────────┘
                 │ HTTP / JSON
┌────────────────▼─────────────────────────┐
│  路由层 (api/routes/)                    │
│  - 接收 HTTP 请求                         │
│  - 校验登录态、CSRF                       │
│  - 调用 Service 层                        │
└────────────────┬─────────────────────────┘
                 │ 函数调用
┌────────────────▼─────────────────────────┐
│  服务层 (services/)                      │
│  - 业务逻辑                               │
│  - 调用数据库 / Docker                    │
└─────────┬──────────────────┬─────────────┘
          │                  │
┌─────────▼─────────┐  ┌─────▼─────────────┐
│  数据层            │  │  Docker SDK        │
│  SQLite (clients) │  │  管理 frpc 容器     │
└───────────────────┘  └───────────────────┘
```

### 1.2 为什么这样分层

- **路由层只管"接请求、返响应"**：不写业务逻辑，便于替换（比如以后改成 GraphQL）
- **服务层只管"做什么"**：不关心 HTTP 细节，可以被命令行、定时任务复用
- **数据层只管"存取"**：不关心业务规则，便于换数据库

每层只依赖下一层，不会反向依赖。这样改一层不会牵连其他层。

### 1.3 请求流转示例

以"创建客户端"为例：

1. 前端 POST `/api/clients`，带 JSON 数据和 CSRF token
2. [clients.py](../app/api/routes/clients.py) 的 `create_client` 函数收到请求
3. 先检查 `login_required()`，未登录返回 401
4. 再检查 `verify_csrf_token()`，CSRF 失败返回 403
5. 调用 `ClientService.create_client(data)`
6. [client_service.py](../app/services/client_service.py) 验证名称、生成 TOML、写入数据库
7. 返回 `{id: 1, message: '创建成功'}`，状态码 201
8. 前端收到响应，跳转到列表页

对应代码：
- 入口：[app/api/routes/clients.py](../app/api/routes/clients.py) `create_client` 函数
- 逻辑：[app/services/client_service.py](../app/services/client_service.py) `create_client` 方法

### 1.4 应用启动流程

对应代码：[app/app.py](../app/app.py)

```
import app.app
  └─ 触发 config.py 的 Config.init()
      └─ 加载管理员密码、创建日志/数据目录
  └─ 创建全局 app = create_app()
      └─ 注册蓝图（auth_bp、clients_bp）
      └─ 注册 SPA 路由
      └─ 注册 teardown_appcontext(close_db)

if __name__ == '__main__':
  └─ init_db()  # 建表
  └─ app.run()  # 启动 Flask
```

---

## 二、数据库设计

### 2.1 表结构

只有一张表 `clients`，存所有客户端配置。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键，自增 |
| name | TEXT | 客户端名称（用户起的，方便识别） |
| config_content | TEXT | frpc 的 TOML 配置内容（核心数据） |
| local_port | INTEGER | 本地端口（展示用，从配置解析） |
| remote_port | INTEGER | 远程端口（展示用，从配置解析） |
| server_addr | TEXT | 服务器地址（展示用） |
| server_port | INTEGER | 服务器端口（默认 7000） |
| token | TEXT | FRP 鉴权 token |
| user | TEXT | FRP 用户名 |
| status | TEXT | 容器状态（stopped/running/error） |
| enabled | BOOLEAN | 是否启用（0/1） |
| frp_version | TEXT | frp 版本号（决定镜像 tag） |
| image | TEXT | 自定义镜像名（覆盖默认） |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

对应代码：[app/models/database.py](../app/models/database.py) 的 `init_db` 函数。

### 2.2 为什么只有一张表

本项目的核心实体只有一个：客户端配置。其他都是配置的属性。

不拆成多表是因为：
- 客户端数量少（通常几个到几十个），不需要关系查询
- 单表查询最快，代码最简单
- 备份/迁移直接复制 `.db` 文件即可

### 2.3 连接管理

不用连接池，用 Flask 的 `g` 对象实现"每请求一连接"：

```python
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(Config.DATABASE_URL)
        ...
    return g.db

def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()
```

在 [app/app.py](../app/app.py) 注册：
```python
app_instance.teardown_appcontext(close_db)
```

这样每个请求结束自动关连接，不会泄露。

对应代码：[app/models/database.py](../app/models/database.py) 的 `get_db` / `close_db`。

### 2.4 数据库迁移

SQLite 不支持复杂的 schema 迁移，本项目用"检查字段是否存在"的轻量方案：

```python
for col_name, col_def in NEED_CHECK_COLUMNS:
    try:
        c.execute('SELECT ' + col_name + ' FROM clients LIMIT 1')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE clients ADD COLUMN ' + col_name + ' ' + col_def)
```

每次启动都跑一遍，老库自动补上新字段。适合字段增加的小改动，不适合字段重命名/删除。

对应代码：[app/models/database.py](../app/models/database.py) 的 `NEED_CHECK_COLUMNS` 和 `init_db`。

### 2.5 性能优化

启用 WAL 模式和 NORMAL 同步：

```python
c.execute('PRAGMA journal_mode=WAL')
c.execute('PRAGMA synchronous=NORMAL')
```

- **WAL**：读不阻塞写，适合 Web 应用"读多写少"
- **NORMAL 同步**：比 FULL 快，崩溃时可能丢最后一笔写操作（可接受）

---

## 三、API 接口

### 3.1 接口列表

#### 认证相关（[app/api/routes/auth.py](../app/api/routes/auth.py)）

| 方法 | 路径 | 说明 | 认证 |
|---|---|---|---|
| GET | `/api/csrf-token` | 获取 CSRF token | 无 |
| GET | `/api/me` | 查询当前登录态 | 无 |
| GET | `/login` | 登录页（返回 SPA HTML） | 无 |
| POST | `/login` | 提交登录 | 无 |
| GET | `/logout` | 登出 | 无 |
| POST | `/api/change-password` | 修改密码 | 登录 + CSRF |

#### 客户端管理（[app/api/routes/clients.py](../app/api/routes/clients.py)）

| 方法 | 路径 | 说明 | 认证 |
|---|---|---|---|
| GET | `/api/clients` | 列出所有客户端 | 登录 |
| POST | `/api/clients` | 创建客户端 | 登录 + CSRF |
| GET | `/api/clients/<id>` | 获取单个客户端 | 登录 |
| PUT | `/api/clients/<id>` | 更新客户端 | 登录 + CSRF |
| DELETE | `/api/clients/<id>` | 删除客户端 | 登录 + CSRF |
| GET | `/api/clients/<id>/config` | 获取配置内容 | 登录 |
| PUT | `/api/clients/<id>/config` | 更新配置内容 | 登录 + CSRF |
| GET | `/api/clients/<id>/status` | 获取容器实时状态 | 登录 |
| POST | `/api/clients/<id>/start` | 启动容器 | 登录 + CSRF |
| POST | `/api/clients/<id>/stop` | 停止容器 | 登录 + CSRF |
| POST | `/api/clients/<id>/restart` | 重启容器 | 登录 + CSRF |
| GET | `/api/clients/<id>/logs` | 获取容器日志 | 登录 |
| POST | `/api/clients/<id>/clear-logs` | 清空日志 | 登录 + CSRF |
| POST | `/api/clients/batch-enable` | 批量启停 | 登录 + CSRF |
| GET | `/api/configs/<id>/export` | 导出配置（给 frpc 用） | API Token |

### 3.2 状态码约定

| 码 | 含义 | 何时返回 |
|---|---|---|
| 200 | 成功 | GET、PUT、DELETE 成功 |
| 201 | 创建成功 | POST 创建资源成功 |
| 302 | 重定向 | 登录成功跳首页 |
| 400 | 请求错误 | 参数校验失败 |
| 401 | 未认证 | 未登录访问受保护接口 |
| 403 | 禁止访问 | CSRF 校验失败 |
| 404 | 资源不存在 | 客户端 ID 不存在 |
| 500 | 服务器错误 | 读日志等意外异常 |

### 3.3 响应格式

统一 JSON：

```json
// 成功
{"message": "操作成功"}
{"id": 1, "message": "创建成功"}
{"clients": [...]}

// 失败
{"error": "失败原因"}
```

### 3.4 认证方式

**Web 浏览器**：通过 session cookie（登录后自动携带）
**frpc 客户端**：通过 Bearer Token（用于 `/api/configs/<id>/export`）

```bash
curl -H "Authorization: Bearer <API_TOKEN>" \
     http://localhost:7600/api/configs/1/export
```

---

## 四、容器管理原理

### 4.1 核心模型

每个客户端对应一个 Docker 容器：

```
数据库 clients 表 (id=1)
        │
        │ ProcessService.deploy_config(1)
        ▼
/opt/frpc/frpc-1.toml  ←── 配置文件（宿主机）
        │
        │ Docker volume mount (ro)
        ▼
容器 FRPC-1 (fatedier/frpc:v0.61.1)
   - 挂载 /etc/frp/frpc.toml:ro
   - network_mode: host
   - restart: always
   - healthcheck: pgrep frpc
```

### 4.2 命名约定

| 资源 | 命名规则 | 示例 |
|---|---|---|
| 容器名 | `FRPC-{id}` | `FRPC-1` |
| 配置文件 | `frpc-{id}.toml` | `frpc-1.toml` |
| 备份文件 | `frpc-{id}.toml.backup.{时间戳}` | `frpc-1.toml.backup.20260806_120000` |

`{id}` 是数据库 `clients.id`，三者通过这个 ID 关联。

对应代码：[app/services/process_service.py](../app/services/process_service.py) 的 `_container_name` / `_config_path`。

### 4.3 启动流程

`ProcessService.start(client_id)` 的步骤：

1. **部署配置**：把数据库里的 `config_content` 写到 `/opt/frpc/frpc-{id}.toml`（覆盖前自动备份）
2. **占位符校验**：检查配置里有没有 `your-server-address` 等未替换的占位符
3. **解析镜像**：按优先级决定用哪个镜像（自定义 > frp_version > 自动获取最新版）
4. **启动容器**：拉镜像 → 清理同名旧容器 → 创建新容器

对应代码：[app/services/process_service.py](../app/services/process_service.py) 的 `start` 方法。

### 4.4 容器参数详解

```python
client.containers.run(
    image,
    command=['-c', '/etc/frp/frpc.toml'],  # frpc 命令参数
    name='FRPC-1',
    network_mode='host',                    # 用宿主机网络
    restart_policy={'Name': 'always'},      # 挂了自动重启
    volumes={
        '/opt/frpc/frpc-1.toml': {
            'bind': '/etc/frp/frpc.toml',
            'mode': 'ro'                    # 只读挂载
        }
    },
    detach=True,
    healthcheck={
        'Test': ['CMD-SHELL', 'pgrep frpc || exit 1'],
        'Interval': 30000000000,            # 30 秒检查一次
        'Timeout': 10000000000,             # 10 秒超时
        'Retries': 3                        # 连续 3 次失败才算 unhealthy
    }
)
```

**为什么 `network_mode='host'`**：frpc 要把远程端口映射到本机端口，用 host 网络最直接，不用做端口映射。

**为什么 `restart_policy='always'`**：宿主机重启后容器自动拉起，保证服务持续可用。

**为什么配置挂载为 `ro`**：frpc 不应改自己的配置，只读防止意外修改。改配置只能通过 Web 控制台（写宿主机文件）。

对应代码：[app/services/process_service.py](../app/services/process_service.py) 的 `_run_container` 方法。

### 4.5 镜像版本解析

优先级（从高到低）：

1. **自定义镜像**（`image` 字段）：完整镜像名，如 `myregistry/frpc:custom`
2. **指定版本**（`frp_version` 字段）：拼成 `fatedier/frpc:{version}`
3. **自动获取最新版**：调 GitHub API 查 fatedier/frp 最新 release

启动成功后把实际用的镜像/版本写回数据库，下次启动不用再查 GitHub。

对应代码：[app/services/process_service.py](../app/services/process_service.py) 的 `_resolve_image` / `get_latest_version` / `_write_back_version`。

### 4.6 状态查询

`get_status` 返回简化的三态：

- `running`：容器在跑且健康检查通过
- `stopped`：容器不存在或已退出
- `error`：容器在跑但健康检查失败

每次查列表时实时查 Docker，不用数据库里的缓存状态。

对应代码：[app/services/process_service.py](../app/services/process_service.py) 的 `get_status`。

---

## 五、安全设计

### 5.1 密码存储

**绝不明文存密码**。用 PBKDF2-HMAC-SHA256 哈希：

```python
# 哈希
salt = secrets.token_hex(32)
dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
hashed = dk.hex()

# 验证
dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
return secrets.compare_digest(dk.hex(), hashed)
```

**为什么用 PBKDF2 而不是 MD5/SHA256**：MD5/SHA256 太快，暴力破解成本低。PBKDF2 迭代 10 万次故意拖慢。

**为什么要盐**：相同密码哈希结果不同，防止彩虹表攻击。

**为什么用 `compare_digest` 而不是 `==`**：防止时序攻击（攻击者通过测量响应时间逐字符猜解）。

对应代码：[app/utils/password.py](../app/utils/password.py)。

### 5.2 登录速率限制

防止暴力破解：

```python
# 每个 IP 失败 5 次，锁定 15 分钟
login_attempts[ip] = {'count': 0, 'locked_until': 0}
```

存在内存里，进程重启清空（可接受）。

对应代码：[app/utils/helpers.py](../app/utils/helpers.py)。

### 5.3 CSRF 防护

每次写操作（POST/PUT/DELETE）要求带 CSRF token：

1. 前端先调 `GET /api/csrf-token` 拿 token
2. 后续写操作在请求头 `X-CSRF-Token` 里带上
3. 服务端用 `hmac.compare_digest` 恒定时间比较

对应代码：[app/services/auth_service.py](../app/services/auth_service.py) 的 `get_csrf_token` / `verify_csrf_token`，[app/api/routes/clients.py](../app/api/routes/clients.py) 的 `verify_csrf_token`。

### 5.4 Session 安全

在 [app/app.py](../app/app.py) 设置：

```python
app_instance.config['SESSION_COOKIE_SAMESITE'] = 'Strict'  # 防止跨站携带
app_instance.config['SESSION_COOKIE_HTTPONLY'] = True      # JS 读不到
app_instance.config['SESSION_COOKIE_SECURE'] = ...         # 仅 HTTPS（生产环境）
```

### 5.5 配置文件权限

部署的配置文件权限设为 `0o600`（仅 owner 可读写），因为里面可能有 token：

```python
os.chmod(config_path, 0o600)
```

对应代码：[app/services/process_service.py](../app/services/process_service.py) 的 `deploy_config`。

### 5.6 SQL 注入防护

所有 SQL 用参数化查询：

```python
# 对
db.execute('SELECT * FROM clients WHERE id = ?', (client_id,))

# 错（不要这样写，会被注入）
db.execute('SELECT * FROM clients WHERE id = ' + str(client_id))
```

对应代码：[app/services/client_service.py](../app/services/client_service.py) 全部 SQL。

---

## 六、测试体系

### 6.1 测试结构

```
tests/
├── conftest.py                # 共享 fixture
├── test_api.py                # API 集成测试
├── test_auth_service.py       # 认证服务测试
├── test_client_service.py     # 客户端服务测试
└── test_helpers.py            # 工具函数测试
```

### 6.2 关键 fixture

在 [tests/conftest.py](../tests/conftest.py) 定义：

- **`clear_login_attempts`**（autouse）：每个测试前清空登录速率限制
- **`mock_docker`**（autouse）：把 `ProcessService._client` 替换成假对象，测试不碰真实 Docker
- **`test_app`**：创建测试用 Flask app，用临时数据库
- **`test_client`**：Flask 测试客户端
- **`test_auth_headers`**：登录后的 headers（cookie 自动携带）

### 6.3 运行测试

```bash
# 跑全部测试
pytest

# 跑单个文件
pytest tests/test_helpers.py

# 跑单个测试
pytest tests/test_auth_service.py::TestAuthIntegration::test_login_logout_flow

# 看覆盖率
pytest --cov=app --cov-report=term-missing
```

### 6.4 mock Docker 的原理

测试不能连真实 Docker（会污染宿主机），所以用 monkeypatch 替换：

```python
class FakeDockerClient:
    def __init__(self):
        self.containers = FakeContainerCollection()
        self.images = FakeImageCollection()

monkeypatch.setattr(ProcessService, '_client', fake_client)
```

这样 `ProcessService._docker()` 返回的是 fake_client，测试可控。

对应代码：[tests/conftest.py](../tests/conftest.py) 的 `mock_docker` fixture。

---

## 七、开发流程

### 7.1 本地开发环境

```bash
# 1. 装后端依赖
pip install -r requirements.txt

# 2. 装前端依赖
cd frontend && npm install

# 3. 跑后端（终端 1）
python app/app.py

# 4. 跑前端（终端 2，热更新）
cd frontend && npm run dev
```

前端开发服务器跑在 5173 端口，会自动把 `/api/*` 代理到后端 7600 端口。

### 7.2 改代码后的验证

```bash
# 后端测试
pytest

# 前端 lint
cd frontend && npm run lint

# 前端测试
cd frontend && npm run test

# 前端构建（部署前必做）
cd frontend && npm run build
```

### 7.3 部署

```bash
docker-compose up -d --build
```

如果容器名冲突：
```bash
docker rm -f frp-console && docker-compose up -d --build
```

### 7.4 调试技巧

**看后端日志**：
```bash
docker-compose logs -f frp-console
```

**进容器查文件**：
```bash
docker exec -it frp-console sh
```

**查 SQLite 数据库**：
```bash
sqlite3 data/frpc.db
> .tables
> SELECT * FROM clients;
```

**查 frpc 容器**：
```bash
docker ps | grep FRPC
docker logs FRPC-1
```

---

## 八、扩展指南

### 8.1 加一个新 API

以"获取客户端统计信息"为例：

**第一步**：在 service 层加方法

```python
# app/services/client_service.py
@staticmethod
def get_stats():
    db = get_db()
    total = db.execute('SELECT COUNT(*) FROM clients').fetchone()[0]
    running = 0
    for c in ClientService.get_all_clients():
        if ProcessService.get_status(c['id']) == 'running':
            running += 1
    return {'total': total, 'running': running}
```

**第二步**：在 route 层加路由

```python
# app/api/routes/clients.py
@clients_bp.route('/api/clients/stats', methods=['GET'])
def get_client_stats():
    if not login_required():
        return jsonify({'error': '未登录'}), 401
    return jsonify(ClientService.get_stats())
```

**第三步**：写测试

```python
# tests/test_api.py
def test_get_stats(test_client, test_auth_headers):
    response = test_client.get('/api/clients/stats')
    assert response.status_code == 200
    assert 'total' in response.json
```

### 8.2 加一个新字段

以"加备注字段"为例：

**第一步**：改表结构

在 [app/models/database.py](../app/models/database.py) 的 `CREATE TABLE` 加字段：
```sql
remark TEXT,
```

在 `NEED_CHECK_COLUMNS` 加：
```python
('remark', 'TEXT'),
```

**第二步**：改 service 层

在 [app/services/client_service.py](../app/services/client_service.py) 的 `create_client` / `update_client` 的 SQL 里加 `remark` 字段。

**第三步**：前端加表单项

在 `frontend/src/pages/` 下相应表单组件加输入框。

**第四步**：跑测试，构建前端，部署

### 8.3 加一个新工具函数

在 [app/utils/](../app/utils/) 下新建文件，比如 `cache.py`：

```python
"""
缓存工具模块
"""
import time

_cache = {}

def set(key, value, ttl=60):
    """设置缓存，ttl 秒后过期"""
    _cache[key] = {'value': value, 'expire': time.time() + ttl}

def get(key):
    """获取缓存，过期返回 None"""
    if key not in _cache:
        return None
    item = _cache[key]
    if time.time() > item['expire']:
        del _cache[key]
        return None
    return item['value']
```

记得写测试 [tests/test_cache.py](../tests/)。

---

## 附录：代码风格约定

1. **变量名**：用简单英文单词或拼音，避免缩写（`client_id` 而不是 `cid`）
2. **注释**：解释"为什么"而不是"是什么"（代码本身能说明是什么）
3. **避免一行式**：宁可多几行也不要写复杂的列表推导
4. **字符串拼接**：用 `+` 而不是 f-string（对初学者更直观）
5. **错误处理**：捕获具体异常，不要裸 `except:`
6. **日志**：用 `ColorLogger`，不要直接 `print`
7. **SQL**：必须用参数化查询，禁止字符串拼接
