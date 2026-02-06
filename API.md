# FRP Console API 文档

## 概述

FRP Console 是一个用于管理 FRP (Fast Reverse Proxy) 客户端的 Web 应用程序。

- 基础 URL: `http://localhost:7600`
- 认证方式: Session Cookie
- 数据格式: JSON

## 认证

所有 API 端点（除了登录相关）都需要认证。使用 Session Cookie 进行身份验证。

### 登录

```http
POST /login
Content-Type: application/x-www-form-urlencoded

username=admin&password=your_password
```

**响应:**
- 成功: 重定向到 `/`
- 失败: 401 Unauthorized

### 获取 CSRF Token

对于修改操作（POST/PUT/DELETE），需要在请求头中包含 CSRF Token。

```http
GET /api/csrf-token
```

**响应:**
```json
{
  "csrf_token": "random_token_string"
}
```

在后续请求中添加请求头:
```http
X-CSRF-Token: random_token_string
```

### 检查登录状态

```http
GET /api/me
```

**响应:**
```json
{
  "authenticated": true,
  "username": "admin"
}
```

### 登出

```http
GET /logout
```

## 客户端管理

### 获取所有客户端

```http
GET /api/clients
```

**响应:**
```json
[
  {
    "id": 1,
    "name": "client-1",
    "config_path": "/opt/frp-console/clients/client-1.toml",
    "local_port": 8080,
    "remote_port": 8080,
    "server_addr": "example.com",
    "status": "running",
    "enabled": 1,
    "always_on": 0,
    "created_at": "2024-01-01 00:00:00",
    "updated_at": "2024-01-01 00:00:00"
  }
]
```

### 获取单个客户端

```http
GET /api/clients/{client_id}
```

**响应:**
```json
{
  "id": 1,
  "name": "client-1",
  "config_path": "/opt/frp-console/clients/client-1.toml",
  "local_port": 8080,
  "remote_port": 8080,
  "server_addr": "example.com",
  "status": "running",
  "enabled": 1,
  "always_on": 0,
  "created_at": "2024-01-01 00:00:00",
  "updated_at": "2024-01-01 00:00:00"
}
```

### 创建客户端

```http
POST /api/clients
Content-Type: application/json
X-CSRF-Token: {csrf_token}

{
  "name": "new-client",
  "server_addr": "example.com",
  "server_port": 7000,
  "local_port": 8080,
  "remote_port": 8080,
  "token": "your-token",
  "user": "your-user-id",
  "always_on": false
}
```

或使用粘贴配置模式:

```http
POST /api/clients
Content-Type: application/json
X-CSRF-Token: {csrf_token}

{
  "name": "new-client",
  "config_content": "[common]\nserver_addr = example.com\nserver_port = 7000\n\n[proxy]\ntype = tcp\nlocal_port = 8080\nremote_port = 8080",
  "always_on": false
}
```

**响应:**
```json
{
  "id": 1,
  "message": "创建成功"
}
```

### 更新客户端

```http
PUT /api/clients/{client_id}
Content-Type: application/json
X-CSRF-Token: {csrf_token}

{
  "name": "updated-name",
  "enabled": 1,
  "always_on": 1
}
```

**响应:**
```json
{
  "message": "更新成功"
}
```

### 删除客户端

```http
DELETE /api/clients/{client_id}
X-CSRF-Token: {csrf_token}
```

**响应:**
```json
{
  "message": "删除成功"
}
```

### 启动客户端

```http
POST /api/clients/{client_id}/start
X-CSRF-Token: {csrf_token}
```

**响应:**
```json
{
  "message": "启动成功 (独立模式，不受网页关闭影响)"
}
```

### 停止客户端

```http
POST /api/clients/{client_id}/stop
X-CSRF-Token: {csrf_token}
```

**响应:**
```json
{
  "message": "停止成功"
}
```

### 重启客户端

```http
POST /api/clients/{client_id}/restart
X-CSRF-Token: {csrf_token}
```

**响应:**
```json
{
  "message": "重启成功"
}
```

### 更新 Always-On 状态

```http
POST /api/clients/{client_id}/always-on
Content-Type: application/json
X-CSRF-Token: {csrf_token}

{
  "always_on": true
}
```

**响应:**
```json
{
  "message": "always_on 状态更新成功"
}
```

### 获取客户端配置

```http
GET /api/clients/{client_id}/config
```

**响应:**
```json
{
  "config": "[common]\nserver_addr = example.com\n..."
}
```

### 更新客户端配置

```http
PUT /api/clients/{client_id}/config
Content-Type: application/json
X-CSRF-Token: {csrf_token}

{
  "config": "[common]\nserver_addr = new.example.com\n..."
}
```

**响应:**
```json
{
  "message": "配置更新成功"
}
```

### 获取客户端日志

```http
GET /api/clients/{client_id}/logs
```

**响应:**
```json
{
  "logs": "[2024-01-01 00:00:00] 启动 frpc\n..."
}
```

## 告警管理

### 获取所有告警

```http
GET /api/alerts
```

**响应:**
```json
[
  {
    "id": 1,
    "client_id": 1,
    "client_name": "client-1",
    "alert_type": "restart_limit",
    "message": "FRP客户端 client-1 5分钟内重启超过3次",
    "sent_to": "admin@example.com",
    "sent_at": "2024-01-01 00:00:00",
    "resolved": 0
  }
]
```

### 标记告警为已解决

```http
POST /api/alerts/{alert_id}/resolve
X-CSRF-Token: {csrf_token}
```

**响应:**
```json
{
  "message": "告警已解决"
}
```

### 清除已解决的告警

```http
POST /api/alerts/clear
X-CSRF-Token: {csrf_token}
```

**响应:**
```json
{
  "message": "已清除已解决的告警"
}
```

## 审计日志

### 获取审计日志

```http
GET /api/audit-logs
```

**响应:**
```json
[
  {
    "id": 1,
    "action": "LOGIN",
    "details": "{\"username\": \"admin\", \"ip\": \"127.0.0.1\"}",
    "level": "INFO",
    "user": "admin",
    "ip_address": "127.0.0.1",
    "user_agent": "Mozilla/5.0...",
    "created_at": "2024-01-01 00:00:00"
  }
]
```

## 管理员设置

### 修改密码

```http
POST /api/change-password
Content-Type: application/json
X-CSRF-Token: {csrf_token}

{
  "old_password": "current_password",
  "new_password": "new_password"
}
```

**响应:**
```json
{
  "message": "密码修改成功"
}
```

## 错误响应

### 401 Unauthorized

未登录或会话已过期。

```json
{
  "error": "未登录，请先登录"
}
```

### 403 Forbidden

CSRF Token 验证失败。

```json
{
  "error": "CSRF 验证失败"
}
```

### 404 Not Found

资源不存在。

```json
{
  "error": "客户端不存在"
}
```

### 400 Bad Request

请求参数错误。

```json
{
  "error": "客户端名称不能为空"
}
```

### 500 Internal Server Error

服务器内部错误。

```json
{
  "error": "启动失败: ..."
}
```

## 速率限制

- 登录尝试: 5 次 / 15 分钟
- 客户端重启: 3 次 / 5 分钟

超出限制将返回 429 Too Many Requests。

## WebSocket

WebSocket 用于实时推送客户端状态更新。

```javascript
const socket = io();

socket.on('connect', () => {
  console.log('Connected to server');
});

socket.on('client_status_update', (data) => {
  console.log('Client status updated:', data);
});
```

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `ADMIN_USER` | 管理员用户名 | admin（自动生成随机密码） |
| `ADMIN_PASSWORD` | 管理员密码 | 随机生成 |
| `SECRET_KEY` | Flask 密钥 | 随机生成 |
| `PORT` | 服务端口 | 7600 |
| `FLASK_ENV` | 运行环境 | production |
| `FORCE_HTTPS` | 强制 HTTPS | false |
| `CORS_ALLOWED_ORIGINS` | 允许的跨域来源 | * |
| `SMTP_HOST` | SMTP 服务器 | 无 |
| `SMTP_PORT` | SMTP 端口 | 587 |
| `SMTP_USER` | SMTP 用户名 | 无 |
| `SMTP_PASSWORD` | SMTP 密码 | 无 |
| `ALERT_TO` | 告警接收邮箱 | 无 |

## 安全注意事项

1. **生产环境必须设置:**
   - `ADMIN_PASSWORD`: 强密码
   - `SECRET_KEY`: 随机密钥
   - `FLASK_ENV=production`
   - `FORCE_HTTPS=true`（如果使用 HTTPS）

2. **CORS 配置:**
   - 生产环境应限制 `CORS_ALLOWED_ORIGINS` 为实际域名

3. **SMTP 配置:**
   - 如需邮件告警，必须配置 SMTP 相关环境变量
