## 目标
将 FRP Console 改造为纯配置管理中心，frpc 完全独立运行，两者彻底解耦。

## 核心原则
- Web 端只管理配置，不控制进程
- frpc 独立运行，自主拉取配置
- Docker 容器重启/删除不影响 frpc

## 改造计划

### 阶段1：Web 端去进程化（核心改造）

#### 1.1 修改 Dockerfile
- 移除 `COPY frpc/ ./frpc/`（不再打包 frp 二进制）
- 移除 `procps` 依赖（不需要进程管理）
- 改为普通端口映射

#### 1.2 重构 process_service.py
- 删除 `start_frpc()`, `stop_frpc()`, `restart_frpc()` 方法
- 删除进程检查相关代码
- 保留配置验证功能

#### 1.3 修改 config.py
- 移除 `FRPC_BINARY` 配置
- 移除 `CONFIGS_DIR` 相关配置
- 添加配置导出 API 认证

#### 1.4 修改 docker-compose.yml
- 移除 `network_mode: host`
- 添加 `ports: - "7600:7600"`
- 简化 volume 挂载

#### 1.5 修改 API 路由
- 移除 `/api/clients/<id>/start`
- 移除 `/api/clients/<id>/stop`
- 移除 `/api/clients/<id>/restart`
- 新增 `/api/configs/<id>/export`（供 frpc 拉取配置）

#### 1.6 修改前端
- 移除启动/停止/重启按钮
- 添加配置下载链接
- 显示配置同步状态

### 阶段2：新增配置导出 API

#### 2.1 创建配置导出接口
```python
GET /api/configs/<id>/export
Header: Authorization: Bearer <token>
Response: TOML 配置内容
```

#### 2.2 添加 API 认证
- 生成固定 token 或支持动态 token
- 限制只有 frpc 能访问配置接口

### 阶段3：创建 frpc 部署工具

#### 3.1 创建独立部署脚本
```bash
# install-frpc.sh
# 1. 下载 frpc 二进制
# 2. 创建 systemd 服务
# 3. 配置自动拉取配置
```

#### 3.2 创建配置同步脚本
```python
# config-sync.py
# 1. 定期从 Web 端拉取配置
# 2. 对比本地配置是否有变化
# 3. 如有变化，更新配置并重启 frpc
```

### 阶段4：数据库简化

#### 4.1 简化 clients 表
```sql
-- 移除 status 字段（不再跟踪进程状态）
-- 移除 always_on 字段（frpc 自己管理）
-- 保留 name, config_content, created_at, updated_at
```

#### 4.2 新增 config_versions 表（可选）
```sql
-- 配置版本历史
CREATE TABLE config_versions (
    id INTEGER PRIMARY KEY,
    client_id INTEGER,
    config_content TEXT,
    created_at TIMESTAMP
);
```

### 阶段5：部署文档

#### 5.1 Web 端部署
```yaml
# docker-compose.yml
version: '3.8'
services:
  frp-console:
    image: ghcr.io/kevin25858/frp-console:latest
    ports:
      - "7600:7600"
    volumes:
      - ./data:/app/data
    environment:
      - ADMIN_PASSWORD=your_password
      - API_TOKEN=secret_token_for_frpc
```

#### 5.2 frpc 部署（宿主机上）
```bash
# 安装 frpc 并配置 systemd
./install-frpc.sh \
  --web-url http://web-server:7600 \
  --client-id 1 \
  --api-token secret_token_for_frpc
```

## 最终架构

```
┌─────────────────────────┐         ┌─────────────────────────┐
│   Docker: Web管理端      │         │   宿主机（或其他服务器）   │
│  ┌─────────────────┐    │         │  ┌─────────────────┐    │
│  │  FRP Console    │    │         │  │  systemd        │    │
│  │  - 配置管理界面  │◄───┼──API────┼──┤  ├─ config-sync  │    │
│  │  - 配置存储      │    │  拉配置  │  │  └─ frpc        │    │
│  │  - 端口7600      │    │         │  └─────────────────┘    │
│  └─────────────────┘    │         │                         │
│                         │         │  容器重启/删除不影响      │
│  可以任意重启/更新       │         │  frpc 持续运行           │
└─────────────────────────┘         └─────────────────────────┘
```

## 实施顺序

1. **阶段1**（Web端去进程化）- 必须完成
2. **阶段2**（配置导出API）- 必须完成
3. **阶段5**（部署文档）- 必须完成
4. **阶段3**（frpc部署工具）- 可选，用户可以手动部署
5. **阶段4**（数据库简化）- 可选优化

## 关键变更点

| 文件 | 变更内容 |
|------|---------|
| Dockerfile | 移除 frpc 二进制，移除 procps |
| docker-compose.yml | 移除 host 网络，添加端口映射 |
| process_service.py | 删除进程管理代码 |
| clients.py API | 移除 start/stop/restart 路由 |
| config.py | 移除 FRPC_BINARY，添加 API_TOKEN |
| 前端界面 | 移除控制按钮，添加配置下载 |

请确认这个方案，我将开始实施具体的代码改造。