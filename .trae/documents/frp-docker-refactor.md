# 重构计划：基于 frp-docker 原理重构 frp-console

## 摘要

将 frp-console 的 frpc 运行模型从「宿主机 systemd + D-Bus」彻底切换为「frpc 跑在 Docker 容器内」（采纳父项目 frpc-docker-deploy 的原理与产物：`fatedier/frpc` 镜像、`--network host`、健康检查、版本自动获取、配置占位符校验、覆盖前备份）。配置文件源路径保持不变：`/etc/frp-client/frpc-{id}.toml`。功能范围为「核心：生成 / 配置 / 管理」，单用户认证，删掉当前全部坏掉的半成高级功能（多用户 RBAC、审计、告警、流量统计、WebSocket、i18n）。同时修复当前无法启动的破损状态。

## 当前状态分析（关键事实）

项目当前处于**半迁移、无法启动**的破损状态：

- [app/app.py](file:///mnt/large_storage/AGitHub/frp-console/app/app.py) 导入 `flask_socketio` 及 6 个不存在的蓝图（`admin`/`audit`/`users`/`service`/`config`/`updates`）、`tasks.*`、`migrations.*`；但 [requirements.txt](file:///mnt/large_storage/AGitHub/frp-console/requirements.txt) 无 `flask-socketio` → 应用无法启动。
- [app/services/client_service.py](file:///mnt/large_storage/AGitHub/frp-console/app/services/client_service.py) 导入不存在的 `AuditLogService`/`AlertService`，引用 `logs`/`alerts` 表与 `always_on` 字段，这些在 [app/models/database.py](file:///mnt/large_storage/AGitHub/frp-console/app/models/database.py) 中都不存在。
- [app/api/routes/clients.py](file:///mnt/large_storage/AGitHub/frp-console/app/api/routes/clients.py) 导入不存在的 `ConfigService`、`utils.log_rotator.ClientLogManager`、`services.process_manager_service.ProcessManagerService`。
- [frontend/src/pages/clients/list.tsx](file:///mnt/large_storage/AGitHub/frp-console/frontend/src/pages/clients/list.tsx) 使用 `react-i18next`，但 [frontend/package.json](file:///mnt/large_storage/AGitHub/frp-console/frontend/package.json) 未安装该依赖 → 前端无法编译。
- [frontend/src/types/index.ts](file:///mnt/large_storage/AGitHub/frp-console/frontend/src/types/index.ts) 定义了 `always_on`/`traffic_in_cache`/`User`/`Alert` 等后端不提供的类型。
- [app/utils/logger.py](file:///mnt/large_storage/AGitHub/frp-console/app/utils/logger.py) CRITICAL 级别含 emoji，违反 workspace 规则（项目内禁止 emoji）。

**完好可复用的部分**（仅做最小改动或不动）：
- [app/api/routes/auth.py](file:///mnt/large_storage/AGitHub/frp-console/app/api/routes/auth.py)、[app/services/auth_service.py](file:///mnt/large_storage/AGitHub/frp-console/app/services/auth_service.py)、[app/utils/decorators.py](file:///mnt/large_storage/AGitHub/frp-console/app/utils/decorators.py)、[app/utils/validators.py](file:///mnt/large_storage/AGitHub/frp-console/app/utils/validators.py)、[app/utils/helpers.py](file:///mnt/large_storage/AGitHub/frp-console/app/utils/helpers.py)、[app/utils/password.py](file:///mnt/large_storage/AGitHub/frp-console/app/utils/password.py)、[app/config.py](file:///mnt/large_storage/AGitHub/frp-console/app/config.py)。
- 前端 [settings.tsx](file:///mnt/large_storage/AGitHub/frp-console/frontend/src/pages/settings.tsx)、[view-config-dialog.tsx](file:///mnt/large_storage/AGitHub/frp-console/frontend/src/pages/clients/view-config-dialog.tsx)（CodeMirror TOML 编辑器，即「配置」UI）。

**两种运行模型对比**：
- 当前 frp-console：frpc 在宿主机以 systemd 模板单元 `frpc-console@{id}.service` 运行，Web 容器通过 D-Bus（`busctl`）+ sudoers 管理进程；需 `setup-host.sh` 准备 systemd 模板、D-Bus 策略、sudoers、`/etc/frp-client` 目录权限。
- 父项目 frpc-docker-deploy：frpc 在 `fatedier/frpc` 容器内运行，`--network host --restart always`，配置挂载为 `/etc/frp/frpc.toml:ro`，健康检查 `pgrep frpc`，自动从 GitHub API 取最新版本，覆盖前备份，启动前占位符校验。

## 目标架构

```
宿主机
├── /var/run/docker.sock                      # 挂载进 Web 容器，用于管理 frpc 容器
├── /etc/frp-client/                          # 配置源目录（路径不变）
│   ├── frpc-1.toml                           # 由 Web 容器写入，权限 600
│   ├── frpc-2.toml
│   └── frpc-1.toml.backup.<ts>               # 覆盖前自动备份
└── Docker 引擎
    ├── frp-console 容器                      # Web 应用（Flask + React SPA），非 root
    │   └── 通过 /var/run/docker.sock 管理下方容器
    └── frpc-console-{id} 容器                # 每个客户端一个，fatedier/frpc:<ver>
        ├── --network host --restart always
        ├── -v /etc/frp-client/frpc-{id}.toml:/etc/frp/frpc.toml:ro
        ├── --health-cmd "pgrep frpc || exit 1"
        └── 启动命令: frpc -c /etc/frp/frpc.toml
```

**关键正确性要点**：Web 容器通过 Docker SDK 创建 frpc 容器时，卷挂载路径是**宿主机路径**。由于 Web 容器把宿主机 `/etc/frp-client` 也挂载到容器内同名路径，Web 应用写文件与 Docker 守护进程解析卷路径二者一致。

**Docker socket 访问**：Web 容器以非 root（appuser, UID 999）运行，通过 `group_add: ["${DOCKER_GID}"]` 加入宿主机 docker 组以读写 socket。`DOCKER_GID` 由用户在 `.env` 中提供（宿主机执行 `stat -c '%g' /var/run/docker.sock` 获取），默认 999。

## 改动清单

### 一、后端

#### 1. [app/app.py](file:///mnt/large_storage/AGitHub/frp-console/app/app.py) — 重写为最小可运行
- 删除所有不存在的导入：`flask_socketio`、`api.routes.{admin,audit,users,service,config,updates}`、`tasks.*`、`migrations.*`、SocketIO 全部代码、后台任务启停。
- 仅注册存在的两个蓝图：`auth_bp`、`clients_bp`。
- 保留：app factory `create_app(testing=False)`、SPA catch-all、init_db() 调用、`Config.init()`。
- 入口 `if __name__ == '__main__'`：`init_db()` 后用 `app.run(host, port, debug=False)`（不再用 socketio.run）。

#### 2. [app/models/database.py](file:///mnt/large_storage/AGitHub/frp-console/app/models/database.py) — 扩展 schema
- `clients` 表新增字段（沿用现有 ALTER TABLE 迁移模式）：
  - `frp_version TEXT DEFAULT 'v0.61.1'`
  - `image TEXT`
- 不新增 `logs`/`alerts`/`users` 表（核心范围不要）。
- 容器名约定为派生量 `frpc-console-{id}`，不入库。

#### 3. [app/services/process_service.py](file:///mnt/large_storage/AGitHub/frp-console/app/services/process_service.py) — 整体替换为 Docker 容器管理
用 Python Docker SDK（`pip install docker`）替代 D-Bus。类名保留 `ProcessService`，方法签名兼容现有调用。落地 frp-docker 全部原理：

```python
import os, urllib.request, json
from docker import from_env, DockerClient
from docker.errors import NotFound, APIError

CONFIGS_DIR = '/etc/frp-client'
FALLBACK_VERSION = 'v0.61.1'

class ProcessService:
    _client: DockerClient | None = None
    @classmethod _docker(cls): return cls._client or from_env()
    @staticmethod _container_name(client_id): return f'frpc-console-{client_id}'
    @staticmethod _config_path(client_id): return os.path.join(CONFIGS_DIR, f'frpc-{client_id}.toml')

    @staticmethod get_latest_version() -> str:
        # GET https://api.github.com/repos/fatedier/frp/releases/latest，解析 tag_name
        # 超时/失败回退 FALLBACK_VERSION

    @staticmethod _resolve_image(client) -> str:
        # 若 client['image'] 非空则用之；否则 f'fatedier/frpc:{client["frp_version"] or get_latest_version()}'

    @staticmethod deploy_config(client_id) -> bool:
        # 读 DB config_content；若文件已存在且内容不同，先 cp 备份为 frpc-{id}.toml.backup.<ts>
        # 写文件，chmod 600

    @staticmethod check_placeholders(config_content) -> tuple[bool, list[str]]:
        # 检查 your-server-address / your-user-token / your-proxy-name 等占位符

    @staticmethod start(client_id) -> tuple[bool, str]:
        # 1) deploy_config(client_id)
        # 2) check_placeholders → 有则拒绝（返回 False, 提示）
        # 3) client = get_client(id); image = _resolve_image(client)
        # 4) docker.images.pull(image)
        # 5) 若容器已存在则 stop+remove
        # 6) docker.containers.run(image, command=['-c','/etc/frp/frpc.toml'],
        #    name=_container_name, network_mode='host', restart_policy={'Name':'always'},
        #    volumes={_config_path: {'bind':'/etc/frp/frpc.toml','mode':'ro'}},
        #    detach=True,
        #    healthcheck={'Test':['CMD-SHELL','pgrep frpc || exit 1'],
        #                 'Interval':30000000000,'Timeout':10000000000,'Retries':3})
        # 7) 回写解析后的 frp_version/image 到 DB

    @staticmethod stop(client_id) -> tuple[bool, str]:
        # 容器存在则 stop+remove（保留配置文件）

    @staticmethod restart(client_id) -> tuple[bool, str]:
        # 容器存在则 recreate（stop+remove+start），等价 frp-docker 重新启动

    @staticmethod get_status(client_id) -> str:
        # docker inspect State.Status + State.Health.Status
        # running → 'running'；exited/created → 'stopped'；unhealthy/failed → 'error'

    @staticmethod get_logs(client_id, lines=1000) -> str:
        # docker logs --tail <lines> <name>（SDK: container.logs(tail=lines)）
        # 容器不存在返回提示串

    @staticmethod clear_logs(client_id) -> tuple[bool, str]:
        # 容器存在则 recreate（stop+remove+start），等价清空 docker stdout 日志
        # 不存在则直接返回成功

    @staticmethod remove_container(client_id) -> bool:
        # stop+remove 容器（删除客户端时调用）
```
- 删除所有 `busctl`/`systemd`/`journalctl`/`sudo` 相关代码。

#### 4. [app/services/client_service.py](file:///mnt/large_storage/AGitHub/frp-console/app/services/client_service.py) — 删除坏依赖
- 删除 `from services.audit_log_service import AuditLogService` 与 `from services.alert_service import AlertService`，及全部 `AuditLogService.log(...)` / `AlertService.send_alert(...)` 调用。
- 删除所有 `always_on` 相关逻辑与字段读写。
- 删除 `delete_client` 中对 `logs`/`alerts` 表的 DELETE 语句。
- `create_client`：
  - 接收可选 `frp_version`、`image`（默认空 → 启动时自动取最新）。
  - 表单生成模式改为生成**新格式 TOML**（`serverAddr`/`serverPort`/`[[proxies]]`），与 fatedier/frpc v0.61+ 兼容；保留粘贴模式。
  - INSERT 语句补 `frp_version`、`image` 列。
- `update_client`：去掉 `always_on`，补 `frp_version`/`image` 可更新。
- `delete_client`：在删 DB 记录前调用 `ProcessService.remove_container(client_id)` 与 `ProcessService` 删除配置文件。

#### 5. [app/api/routes/clients.py](file:///mnt/large_storage/AGitHub/frp-console/app/api/routes/clients.py) — 修复导入与路由
- 删除 `from services.process_service import ConfigService`、`from utils.log_rotator import ClientLogManager`、`from services.process_manager_service import ProcessManagerService`。
- 改为 `from services.process_service import ProcessService`。
- `start/stop/restart` 路由调用 `ProcessService.start/stop/restart(client_id)`。
- `get_client_logs` 路由调用 `ProcessService.get_logs(client_id)`。
- 新增 `POST /api/clients/<id>/clear-logs` 路由 → `ProcessService.clear_logs(client_id)`（[view-logs-dialog.tsx](file:///mnt/large_storage/AGitHub/frp-console/frontend/src/pages/clients/view-logs-dialog.tsx) 已调用此端点）。
- 新增 `POST /api/clients/batch-enable` 路由（[dashboard.tsx](file:///mnt/large_storage/AGitHub/frp-console/frontend/src/pages/dashboard.tsx) 已调用）：入参 `{enabled: bool}`；`enabled=true` 时对所有客户端 `ProcessService.start`，`false` 时 `ProcessService.stop`，并更新 `enabled` 字段。
- 保留现有 `export_client_config`（`/api/configs/<id>/export`，Bearer Token），不动。

#### 6. [requirements.txt](file:///mnt/large_storage/AGitHub/frp-console/requirements.txt) — 新增 Docker SDK
- 增加 `docker==7.1.0`。其余保持。

#### 7. [app/utils/logger.py](file:///mnt/large_storage/AGitHub/frp-console/app/utils/logger.py) — 去 emoji
- CRITICAL 级别图标 `'🔥'` 改为非 emoji 字符（如 `'!!'` 或 `'x'`）。

### 二、前端

#### 1. [frontend/src/types/index.ts](file:///mnt/large_storage/AGitHub/frp-console/frontend/src/types/index.ts)
- `Client` 删除 `always_on`、`traffic_in_cache`、`traffic_out_cache`、`connections_active_cache`、`config_path`；新增 `frp_version?: string`、`image?: string`。
- 删除 `AlertType`/`Alert`/`AlertStats`、`UserRole`/`User`/`CreateUserFormData`/`UpdateUserFormData`/`ResetPasswordFormData`、`CreateClientFormData`/`UpdateClientFormData` 中的 `always_on`。
- `CreateClientFormData` 新增可选 `frp_version?`、`image?`。

#### 2. [frontend/src/pages/clients/list.tsx](file:///mnt/large_storage/AGitHub/frp-console/frontend/src/pages/clients/list.tsx) — 修复编译
- 删除 `import { useTranslation } from "react-i18next"` 与 `const { t } = useTranslation()`。
- 将所有 `t('clients.xxx')`/`t('common.xxx')` 替换为字面量中文字符串（与 settings.tsx 风格一致）。
- 其余结构（表格、启动/停止/重启、查看配置、查看日志、删除、移动端卡片）保持不变。

#### 3. [frontend/src/pages/clients/add-client-dialog.tsx](file:///mnt/large_storage/AGitHub/frp-console/frontend/src/pages/clients/add-client-dialog.tsx) — 增加「生成」与版本
- 增加「粘贴配置 / 表单生成」模式切换（Tabs 或 Select）。
  - 粘贴模式：现状（name + config_content）。
  - 表单模式：server_addr、server_port、token、user、proxy_name、local_port、remote_port → 提交时由后端生成新格式 TOML。
- 增加可选 `frp_version` 输入框，placeholder `auto（最新版）`，留空表示自动。
- 提交体：`{ name, config_content?, server_addr?, server_port?, token?, user?, proxy_name?, local_port?, remote_port?, frp_version? }`。

#### 4. [frontend/src/pages/dashboard.tsx](file:///mnt/large_storage/AGitHub/frp-console/frontend/src/pages/dashboard.tsx)
- 统计卡片字段已是 `enabled`/`status`，无需改类型；`handleBatchEnable` 调用 `/clients/batch-enable`（后端已新增）。无改动或仅核对。

#### 5. 删除冗余文件
- [frontend/src/pages/clients/edit-config-dialog.tsx](file:///mnt/large_storage/AGitHub/frp-console/frontend/src/pages/clients/edit-config-dialog.tsx)：未被引用（list.tsx 用 ViewConfigDialog），删除以减负。

#### 6. 其它前端文件
- [view-config-dialog.tsx](file:///mnt/large_storage/AGitHub/frp-console/frontend/src/pages/clients/view-config-dialog.tsx)、[view-logs-dialog.tsx](file:///mnt/large_storage/AGitHub/frp-console/frontend/src/pages/clients/view-logs-dialog.tsx)、[settings.tsx](file:///mnt/large_storage/AGitHub/frp-console/frontend/src/pages/settings.tsx)、[login.tsx](file:///mnt/large_storage/AGitHub/frp-console/frontend/src/pages/login.tsx)、[lib/api.ts](file:///mnt/large_storage/AGitHub/frp-console/frontend/src/lib/api.ts)、[hooks/useApi.ts](file:///mnt/large_storage/AGitHub/frp-console/frontend/src/hooks/useApi.ts)：保持不动（核对即可）。

### 三、部署

#### 1. [docker-compose.yml](file:///mnt/large_storage/AGitHub/frp-console/docker-compose.yml)
- 删除卷挂载：`/run/dbus/system_bus_socket`、`/run/systemd`、`/var/log/journal`、`/etc/machine-id`。
- 删除 `security_opt: apparmor=unconfined`。
- 新增卷挂载：`/var/run/docker.sock:/var/run/docker.sock`。
- 保留：`./data:/app/data`、`./logs:/app/logs`、`/etc/frp-client:/etc/frp-client`。
- 新增 `group_add: ["${DOCKER_GID:-999}"]`。
- `.env.example` 增加 `DOCKER_GID=999` 与说明（见下）。

#### 2. [Dockerfile](file:///mnt/large_storage/AGitHub/frp-console/Dockerfile)
- 系统依赖：删除 `dbus systemd`，仅保留 `curl sudo`（如 sudo 不再使用则一并删除）。不再 `COPY sudoers-frp-console`。
- 用户：保留非 root appuser（UID 999）。不再需要 `systemd-journal` 组。
- 其余（多阶段前端构建、Python 依赖、HEALTHCHECK、CMD）保持。

#### 3. [setup-host.sh](file:///mnt/large_storage/AGitHub/frp-console/setup-host.sh) — 大幅简化
- 删除：systemd 模板单元、D-Bus 策略、sudoers、systemctl daemon-reload。
- 仅保留：
  1. `mkdir -p /etc/frp-client && chown -R 999:999 /etc/frp-client && chmod 755 /etc/frp-client`
  2. 打印提示：宿主机执行 `stat -c '%g' /var/run/docker.sock` 获取 DOCKER_GID 并写入 `.env`。
  3. 提示执行 `docker compose up -d --build`。

#### 4. [.env.example](file:///mnt/large_storage/AGitHub/frp-console/.env.example)
- 新增 `DOCKER_GID=999` 及注释说明（宿主机 docker 组 GID）。

#### 5. 删除无用文件
- `sudoers-frp-console`（不再需要 sudo busctl/journalctl）。
- `scripts/install-frpc.sh`（远程拉取模型，用户未选）。
- `init_db.py`（DB 启动自动初始化，且其内容引用旧 schema/表，过时）。

#### 6. 待执行时核对的可留文件
- `frp-console.conf.example`（env 示例，无害，保留）。
- `frpc/LICENSE`、`frpc-console`、`install.sh`、`scripts/update.sh`：执行时快速判定，若为旧模型残留且无引用则删除。

### 四、测试

#### 1. [tests/conftest.py](file:///mnt/large_storage/AGitHub/frp-console/tests/conftest.py)
- `test_database` fixture 的 CREATE TABLE 语句补 `frp_version`、`image` 列。
- `test_app` fixture：修复认证 — 用 `utils.password.hash_password('test_password')` 生成真实 salt/hash 赋给 `Config.PASSWORD_SALT`/`Config.ADMIN_PASSWORD`，使 `test_auth_headers` 可登录。
- 新增 `mock_docker` autouse fixture：用 `monkeypatch` 把 `services.process_service.ProcessService` 的 `_docker`/`_client` 替换为伪对象（伪 containers/images），避免测试触碰真实 Docker。

#### 2. [tests/test_api.py](file:///mnt/large_storage/AGitHub/frp-console/tests/test_api.py)、[tests/test_client_service.py](file:///mnt/large_storage/AGitHub/frp-console/tests/test_client_service.py)
- 移除对 `always_on`/`logs`/`alerts`/`export` 的过时断言。
- 对涉及容器操作的用例，断言调用了 mock docker 的对应方法（start/stop/remove/run），而非真实进程。
- 新增：`POST /api/clients/batch-enable`、`POST /api/clients/<id>/clear-logs` 的基础用例。

#### 3. [tests/test_auth_service.py](file:///mnt/large_storage/AGitHub/frp-console/tests/test_auth_service.py)、[tests/test_helpers.py](file:///mnt/large_storage/AGitHub/frp-console/tests/test_helpers.py)
- 这两个不涉及 docker，预期无须大改；执行时跑通即可。

### 五、文档

#### 1. [CLAUDE.md](file:///mnt/large_storage/AGitHub/frp-console/CLAUDE.md)
- 「High-level architecture」段：frpc 运行模型改为「fatedier/frpc 容器内运行，Web 容器通过 docker.sock 管理」；删除「宿主机 systemd / frpc-{id}.service / D-Bus」描述。
- 配置路径描述保持 `/etc/frp-client/frpc-{id}.toml`。
- Common commands：保留；Docker 段保留 `docker-compose up -d --build`。

#### 2. [README.md](file:///mnt/large_storage/AGitHub/frp-console/README.md)
- 系统架构图改为 Docker 容器模型。
- 删除「宿主机 systemd 服务 / setup-host.sh 初始化 D-Bus」段落，改为简化版 setup-host（仅建目录 + DOCKER_GID）。
- 新增「frpc 容器由 Web 控制台通过 docker.sock 管理」说明。
- API 表保持（端点不变）。

## frp-docker 原理落地映射

| frp-docker 原理 | 本项目落地 |
|---|---|
| fatedier/frpc 镜像运行 frpc | `ProcessService.start` 用 Docker SDK `containers.run` |
| `--network host --restart always` | `network_mode='host'`，`restart_policy={'Name':'always'}` |
| 配置挂载 `/etc/frp/frpc.toml:ro` | 卷 `{config_path: {'bind':'/etc/frp/frpc.toml','mode':'ro'}}` |
| 健康检查 `pgrep frpc` | `healthcheck={'Test':['CMD-SHELL','pgrep frpc \|\| exit 1'],...}` |
| GitHub API 取最新版本 | `ProcessService.get_latest_version()`（urllib，回退 v0.61.1） |
| 占位符校验拒绝启动 | `ProcessService.check_placeholders()`，start 前校验 |
| 覆盖前 `.backup.<ts>` 备份 | `deploy_config()` 写入前若内容变化先备份 |
| 配置路径 `/opt/frpc/<name>.toml` | **不变**：保持 `/etc/frp-client/frpc-{id}.toml` |
| 容器名 `<name>` | `frpc-console-{id}` |

## 假设与决策

1. **运行模型**：仅 Docker 容器模型，完全移除 systemd/D-Bus/sudoers（用户已确认）。
2. **功能范围**：核心「生成/配置/管理」+ 单用户认证；删掉多用户、审计、告警、流量、WebSocket、i18n（用户已确认）。
3. **配置路径**：`/etc/frp-client/frpc-{id}.toml` 不变（用户额外要求「配置文件源路径也不要变」）。DB `config_content` 仍为单一真相源，部署时写出到该文件。
4. **日志**：用 `docker logs`（stdout）读取；`clear-logs` 通过 recreate 容器实现（会短暂中断隧道，属可接受语义）。不挂载日志卷、不写入日志文件，保持简单。
5. **Docker 访问**：Python Docker SDK（`docker==7.1.0`）+ 挂载 `/var/run/docker.sock` + `group_add` DOCKER_GID；Web 容器保持非 root。
6. **版本管理**：每客户端可指定 `frp_version`，留空则启动时自动取最新并回写 DB；默认回退 `v0.61.1`。
7. **表单生成模式**：生成新格式 TOML（`serverAddr`/`serverPort`/`[[proxies]]`），兼容 frpc v0.52+。
8. **保留 export 端点**：`/api/configs/<id>/export` 保留不动（无害、小，供手动拉取）。
9. **容器命名**：`frpc-console-{id}`，与 Web 容器 `frp-console` 区分，便于按 id 追溯。
10. **emoji**：移除 logger.py 中的 emoji 以遵守 workspace 规则。

## 验证步骤

1. **后端单测**：项目根 `pytest`，全部通过（含 mock docker）。
2. **前端构建与测试**：`cd frontend && npm run build && npm run lint && npm run test`，编译无 `react-i18next` 报错。
3. **本地起服务**（需要 Docker）：
   - `cp .env.example .env`，填 `ADMIN_PASSWORD`/`SECRET_KEY`/`API_TOKEN`/`DOCKER_GID`。
   - `sudo bash setup-host.sh`（仅建目录 + 提示）。
   - `docker-compose up -d --build`。
4. **端到端**：
   - 登录 Web → 添加客户端（粘贴一段真实 frpc TOML）→ 列表出现。
   - 点「启动」→ `docker ps` 见 `frpc-console-1` 运行，健康态；状态显示 running。
   - 点「查看日志」→ 看到 frpc stdout 日志。
   - 改配置 → 保存 → 重启 → `docker exec` 验证容器内 `/etc/frp/frpc.toml` 已更新，旧配置存在 `.backup.*`。
   - 占位符配置（含 `your-server-address`）启动应被拒绝并提示。
   - 停止 → 容器被 remove；删除客户端 → 容器与配置文件一并清除。
   - 仪表盘「启用全部/禁用全部」批量生效。
5. **回归**：`docker-compose down` 后 `docker-compose up -d`，`--restart always` 的 frpc 容器随宿主机/Docker 自动恢复（核心范围不做 Web 侧自动拉起）。

## 执行顺序（Todo）

1. 后端：app.py 重写 → database.py 扩字段 → process_service.py 替换为 Docker → client_service.py 去坏依赖 → clients.py 修路由 → requirements.txt 加 docker → logger.py 去 emoji。
2. 前端：types 清理 → list.tsx 去 i18n → add-client-dialog 增模式与版本 → 删 edit-config-dialog.tsx → 核对 dashboard。
3. 部署：docker-compose.yml → Dockerfile → setup-host.sh → .env.example → 删除 sudoers/install-frpc.sh/init_db.py。
4. 测试：conftest（mock docker + 真实密码 hash）→ test_api/test_client_service 更新 → 跑通 pytest。
5. 文档：CLAUDE.md → README.md。
6. 验证：前端 build/lint/test → 后端 pytest → docker-compose 起服务端到端。
