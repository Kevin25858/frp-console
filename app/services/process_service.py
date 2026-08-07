"""
进程服务模块
通过 Docker SDK 管理 frpc 客户端容器

frpc 以 fatedier/frpc 容器方式运行：
- --network host --restart always
- 配置挂载 /opt/frpc/frpc-{id}.toml -> /etc/frp/frpc.toml:ro
- 健康检查 pgrep frpc
- 自动获取最新 frp 版本（回退 v0.61.1）
- 启动前占位符校验
- 覆盖前自动备份配置

为什么用 Docker 而不是直接跑 frpc 进程：
    1. 隔离：每个 frpc 在独立容器里，互不影响
    2. 版本管理：不同客户端可以用不同版本的 frpc
    3. 自动重启：容器挂了 Docker 会自动拉起
    4. 易清理：删容器就彻底清理，不会残留进程/文件

为什么用 Docker SDK 而不是 subprocess 调 docker 命令：
    1. 不需要解析命令行输出，直接拿到 Python 对象
    2. 错误处理更精细（异常类型而非退出码）
    3. 性能更好（不用每次启动子进程）

为什么配置文件挂载为只读（mode: 'ro'）：
    frpc 不应该改自己的配置，只读挂载防止容器内进程意外修改。
    修改配置只能通过 Web 控制台（写宿主机的文件）。
"""
import os
import json
import urllib.request
from docker import from_env
from docker.errors import NotFound, APIError

from utils.logger import ColorLogger
from models.database import get_db


# 配置目录（可通过环境变量覆盖，默认 /opt/frpc）
# 所有客户端的配置文件都放这里，命名规则：frpc-{id}.toml
CONFIGS_DIR = os.environ.get('FRP_CONFIGS_DIR', '/opt/frpc')

# 默认版本（获取最新版本失败时用这个）
# 网络不通时回退到这个稳定版本，保证可用
FALLBACK_VERSION = 'v0.61.1'

# 默认镜像名
DEFAULT_IMAGE = 'fatedier/frpc:' + FALLBACK_VERSION

# GitHub API 地址，用于获取最新版本号
# fatedier/frp 是 frp 项目的官方仓库
GITHUB_LATEST_URL = 'https://api.github.com/repos/fatedier/frp/releases/latest'

# 占位符列表（来自 frp-docker 模板，启动前必须被替换）
# 用途：用户用模板创建配置后，必须把占位符换成实际值才能启动
#       防止用默认值跑起来连不上服务器
PLACEHOLDERS = ['your-server-address', 'your-user-token', 'your-proxy-name']


class ProcessService:
    """frpc 容器管理服务"""

    # Docker 客户端单例
    # 用类变量保存，避免每次操作都创建新连接
    _client = None

    # -------------------- 内部工具 --------------------

    @classmethod
    def _docker(cls):
        """
        获取 Docker 客户端（可被测试 monkeypatch 替换）

        为什么用 classmethod 而不是 staticmethod：
            classmethod 能访问 cls，可以读/写类属性 _client
            staticmethod 不能访问类属性，无法实现单例

        为什么用懒加载（第一次调用才创建）：
            1. 模块导入时不连 Docker，避免无 Docker 环境下 import 失败
            2. 测试时可以替换 _client 为 mock 对象
        """
        if cls._client is None:
            # from_env 从环境变量读 Docker 连接配置
            # 通常连接 /var/run/docker.sock
            cls._client = from_env()
        return cls._client

    @staticmethod
    def _get_name(client_id):
        """根据客户端 ID 获取客户端 name，找不到时回退为 {id}"""
        record = ProcessService._get_client_record(client_id)
        if record and record['name']:
            return record['name']
        return str(client_id)

    @staticmethod
    def _container_name(client_id):
        """
        根据客户端 name 生成容器名

        命名规则：FRPC-{name}
          - 大写前缀 FRPC- 标识这是本工具管理的 frpc 容器
          - {name} 取自数据库 clients.name，与用户自定义名称一致
          - 保留用户原有名称（如 MC5173FRP-SQ1 -> FRPC-MC5173FRP-SQ1）
          - 防止重名导致冲突：name 唯一
        """
        return 'FRPC-' + ProcessService._get_name(client_id)

    @staticmethod
    def _config_path(client_id):
        """根据客户端 name 生成配置文件路径（保留原名，加 frpc- 前缀）"""
        return os.path.join(CONFIGS_DIR, 'frpc-' + ProcessService._get_name(client_id) + '.toml')

    @classmethod
    def _get_container(cls, client_id):
        """获取容器对象，不存在返回 None"""
        try:
            return cls._docker().containers.get(cls._container_name(client_id))
        except NotFound:
            # 容器不存在是正常情况（客户端没启动）
            return None
        except APIError as e:
            # 其他错误（如 Docker 服务挂了）记日志但不抛出
            ColorLogger.warning('查询容器 ' + str(client_id) + ' 失败: ' + str(e), 'Process')
            return None

    @staticmethod
    def _get_client_record(client_id):
        """从数据库读取客户端记录"""
        db = get_db()
        return db.execute(
            'SELECT * FROM clients WHERE id = ?', (client_id,)
        ).fetchone()

    @staticmethod
    def _resolve_image(client):
        """
        解析镜像和版本号

        优先级：
          1. 自定义镜像（image 字段）
          2. 指定版本（frp_version 字段）
          3. 自动获取最新版本

        返回:
            (镜像名, 版本号)
        """
        # 优先使用自定义镜像
        # 用户可以指定完整的镜像名，比如用别的仓库或带 digest
        image = None
        if client and client['image']:
            image = client['image']

        if image:
            # 从镜像名提取版本号（冒号后面的部分）
            # 比如 'fatedier/frpc:v0.61.1' -> 'v0.61.1'
            if ':' in image:
                version = image.split(':')[-1]
            else:
                version = FALLBACK_VERSION
            return image, version

        # 没有自定义镜像，用 frp_version 或自动获取最新版本
        version = None
        if client and client['frp_version']:
            version = client['frp_version']

        if not version:
            # 数据库里没记录版本，去 GitHub 查最新版
            version = ProcessService.get_latest_version()

        image = 'fatedier/frpc:' + version
        return image, version

    @staticmethod
    def _write_back_version(client_id, image, version):
        """
        把解析后的镜像名和版本号写回数据库

        为什么写回：
            1. 下次启动不用再查 GitHub（节省网络请求）
            2. 用户可以看到实际用的版本
            3. 自动获取的版本固定下来，避免版本漂移
        """
        db = get_db()
        db.execute(
            'UPDATE clients SET image = ?, frp_version = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (image, version, client_id)
        )
        db.commit()

    # -------------------- frp-docker 原理落地 --------------------

    @staticmethod
    def get_latest_version():
        """从 GitHub API 获取 frp 最新版本号，失败回退 FALLBACK_VERSION"""
        try:
            req = urllib.request.Request(
                GITHUB_LATEST_URL,
                # User-Agent 是 GitHub API 的要求，没设置会被拒绝
                headers={'User-Agent': 'frp-console', 'Accept': 'application/vnd.github+json'}
            )
            # timeout=5：最多等 5 秒，避免网络问题卡住启动流程
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            tag = data.get('tag_name', '')
            if tag:
                # 确保版本号以 v 开头
                # GitHub release 的 tag_name 通常形如 'v0.61.1'
                # 但保险起见统一加 v 前缀
                if tag.startswith('v'):
                    return tag
                else:
                    return 'v' + tag
        except Exception as e:
            # 网络问题、API 限流、JSON 解析失败等，都回退到默认版本
            # 保证即使网络不通也能启动
            ColorLogger.warning(
                '获取 frp 最新版本失败，使用回退版本 ' + FALLBACK_VERSION + ': ' + str(e),
                'Process'
            )
        return FALLBACK_VERSION

    @staticmethod
    def check_placeholders(config_content):
        """
        检查配置是否包含未修改的占位符

        返回:
            (是否通过, 找到的占位符列表)

        为什么检查占位符：
            用户用模板创建配置后，可能忘了替换占位符就启动，
            会导致 frpc 用错误配置跑起来，连不上服务器还难排查。
            启动前检查可以早失败、早反馈。
        """
        found = []
        for ph in PLACEHOLDERS:
            if ph in config_content:
                found.append(ph)
        ok = len(found) == 0
        return ok, found

    @staticmethod
    def deploy_config(client_id):
        """
        把数据库中的配置写入 /opt/frpc/frpc-{id}.toml（覆盖前自动备份）

        为什么要把配置写到文件再挂载：
            Docker 容器无法直接读数据库，必须通过文件挂载。
            所以"数据库 -> 文件 -> 容器"是标准流程。
        """
        record = ProcessService._get_client_record(client_id)
        if not record:
            return False

        config_content = record['config_content']
        if not config_content:
            config_content = ''

        # 确保配置目录存在
        # 首次运行时 /opt/frpc 可能不存在
        os.makedirs(CONFIGS_DIR, exist_ok=True)
        config_path = ProcessService._config_path(client_id)

        # 如果旧文件内容和新内容不同，先备份旧文件
        # 防止误操作覆盖了正确的配置，备份后还能恢复
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    old_content = f.read()
                # 只有内容真的变了才备份，避免无意义的备份文件堆积
                if old_content != config_content and old_content.strip():
                    import time
                    # 备份文件名带时间戳，保留所有历史版本
                    backup_path = config_path + '.backup.' + time.strftime('%Y%m%d_%H%M%S')
                    os.replace(config_path, backup_path)
                    ColorLogger.info('已备份原配置到 ' + backup_path, 'Process')
        except Exception as e:
            # 备份失败不中断流程，继续写新配置
            # 因为新配置是权威的，宁可丢旧备份也要写新配置
            ColorLogger.warning('备份配置失败（继续写入）: ' + str(e), 'Process')

        # 写入新配置
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            # chmod 600：只有 owner 能读写，防止其他用户看到配置（可能有 token）
            os.chmod(config_path, 0o600)
            ColorLogger.info('客户端 ' + str(client_id) + ' 配置已部署到 ' + config_path, 'Process')
            return True
        except Exception as e:
            ColorLogger.error('部署配置失败: ' + str(e), 'Process')
            return False

    @staticmethod
    def remove_config(client_id):
        """删除 /opt/frpc/frpc-{id}.toml"""
        config_path = ProcessService._config_path(client_id)
        try:
            if os.path.exists(config_path):
                os.remove(config_path)
                ColorLogger.info('客户端 ' + str(client_id) + ' 配置文件已删除', 'Process')
            return True
        except Exception as e:
            ColorLogger.error('删除配置文件失败: ' + str(e), 'Process')
            return False

    # -------------------- 容器生命周期 --------------------

    @staticmethod
    def _run_container(client_id, image):
        """拉取镜像并启动容器"""
        client = ProcessService._docker()

        # 拉取镜像
        # 本地没有这个镜像时会从 Docker Hub 下载
        try:
            ColorLogger.info('拉取镜像: ' + image, 'Process')
            client.images.pull(image)
        except APIError as e:
            return False, '镜像拉取失败: ' + str(e)

        # 清理同名旧容器
        # Docker 不允许同名容器并存，启动前必须清理
        # 比如容器已经退出但没 remove，就要先删掉
        old = ProcessService._get_container(client_id)
        if old:
            try:
                old.stop()
            except Exception:
                pass
            try:
                old.remove()
            except Exception:
                pass

        # 创建并启动新容器
        try:
            client.containers.run(
                image,
                # frpc 命令参数：-c 指定配置文件路径
                command=['-c', '/etc/frp/frpc.toml'],
                name=ProcessService._container_name(client_id),
                # network_mode='host'：用宿主机网络
                # 为什么用 host 网络：
                #   frpc 要把远程端口映射到本地端口，
                #   用 host 网络最简单，不需要做端口映射
                network_mode='host',
                # restart_policy='always'：容器挂了自动重启
                # 包括宿主机重启后也会自动拉起
                restart_policy={'Name': 'always'},
                volumes={
                    ProcessService._config_path(client_id): {
                        'bind': '/etc/frp/frpc.toml',
                        # 'ro' = read-only，容器内只能读不能写
                        'mode': 'ro'
                    }
                },
                detach=True,
                # 健康检查：用 pgrep 命令检查 frpc 进程是否存活
                # Interval 单位是纳秒，30000000000 = 30 秒
                # Timeout 10000000000 = 10 秒
                # Retries 3：连续 3 次失败才标记为 unhealthy
                healthcheck={
                    'Test': ['CMD-SHELL', 'pgrep frpc || exit 1'],
                    'Interval': 30000000000,
                    'Timeout': 10000000000,
                    'Retries': 3,
                },
            )
            return True, '启动成功'
        except APIError as e:
            return False, '容器启动失败: ' + str(e)

    @staticmethod
    def start(client_id):
        """启动客户端容器"""
        # 第一步：部署配置文件
        # 必须先把配置写到文件，容器才能挂载
        if not ProcessService.deploy_config(client_id):
            return False, '配置部署失败'

        # 第二步：占位符校验
        record = ProcessService._get_client_record(client_id)
        if not record:
            return False, '客户端不存在'

        config_content = record['config_content']
        if not config_content:
            config_content = ''

        # 检查配置里有没有未替换的占位符
        ok, found = ProcessService.check_placeholders(config_content)
        if not ok:
            return False, '配置包含未修改的占位符: ' + ', '.join(found) + '，请先编辑配置'

        # 第三步：解析镜像
        # 决定用哪个镜像、哪个版本
        image, version = ProcessService._resolve_image(record)

        # 第四步：启动容器
        ok, msg = ProcessService._run_container(client_id, image)
        if ok:
            # 启动成功后把实际用的镜像/版本写回数据库
            ProcessService._write_back_version(client_id, image, version)
            ColorLogger.success('客户端 ' + str(client_id) + ' 容器已启动 (' + image + ')', 'Process')
            return True, '启动成功'

        ColorLogger.warning('客户端 ' + str(client_id) + ' 启动失败: ' + msg, 'Process')
        return False, msg

    @staticmethod
    def stop(client_id):
        """停止并移除容器（保留配置文件）"""
        container = ProcessService._get_container(client_id)
        if not container:
            # 容器不存在视为已停止，幂等操作
            return True, '容器未运行'

        try:
            try:
                # timeout=10：给 frpc 10 秒优雅退出
                # 超时后 Docker 会发 SIGKILL 强制杀
                container.stop(timeout=10)
            except Exception:
                pass
            # remove 把容器彻底删掉，否则会留下 exited 状态的容器
            container.remove()
            ColorLogger.success('客户端 ' + str(client_id) + ' 容器已停止', 'Process')
            return True, '停止成功'
        except APIError as e:
            return False, '停止失败: ' + str(e)

    @staticmethod
    def restart(client_id):
        """重启容器（重新创建，等价于 frp-docker 重新启动）"""
        record = ProcessService._get_client_record(client_id)
        if not record:
            return False, '客户端不存在'

        # 重新部署配置（覆盖前会备份）
        # 这样即使配置改了，重启后容器用的是最新配置
        if not ProcessService.deploy_config(client_id):
            return False, '配置部署失败'

        image, version = ProcessService._resolve_image(record)
        ok, msg = ProcessService._run_container(client_id, image)
        if ok:
            ProcessService._write_back_version(client_id, image, version)
            ColorLogger.success('客户端 ' + str(client_id) + ' 容器已重启 (' + image + ')', 'Process')
            return True, '重启成功'

        return False, msg

    @staticmethod
    def get_status(client_id):
        """
        获取容器状态: running / stopped / error

        为什么返回简化的三态而不是 Docker 的完整状态：
            前端列表只需要这三种状态来显示图标/颜色，
            Docker 的 'created'/'paused'/'exited' 等细节对用户没意义。
        """
        container = ProcessService._get_container(client_id)
        if not container:
            return 'stopped'

        try:
            # reload 从 Docker 守护进程拉取最新状态
            # container 对象可能是缓存的旧状态
            container.reload()
            state = container.attrs.get('State', {})
            status = state.get('Status', '')
            health = state.get('Health', {}).get('Status', '')

            if status == 'running':
                # 运行中还要看健康检查
                # frpc 进程可能崩了但容器还活着
                if health == 'unhealthy':
                    return 'error'
                return 'running'

            if status == 'exited' or status == 'created':
                return 'stopped'

            if status == 'failed' or health == 'unhealthy':
                return 'error'

            return 'stopped'
        except Exception:
            return 'stopped'

    @staticmethod
    def get_logs(client_id, lines=1000):
        """读取容器 stdout 日志"""
        container = ProcessService._get_container(client_id)
        if not container:
            name = ProcessService._container_name(client_id)
            # 给用户一个排查提示，告诉他可以用 docker logs 命令查看
            return '日志暂无记录（容器可能尚未启动）。可在宿主机执行: docker logs ' + name

        try:
            # tail=lines 只取最后 N 行，避免日志太大
            data = container.logs(tail=lines, timestamps=False)
            if isinstance(data, bytes):
                # Docker SDK 返回 bytes，要解码成字符串
                # errors='replace'：遇到非法字符用 ? 替代，避免解码失败
                return data.decode('utf-8', errors='replace')
            return str(data)
        except APIError as e:
            return '读取日志失败: ' + str(e)

    @staticmethod
    def clear_logs(client_id):
        """
        清空日志（通过重新创建容器来清空 docker stdout 日志）

        为什么不直接删日志文件：
            Docker 的 stdout 日志由 Docker 守护进程管理，
            不能直接删文件（会影响 Docker 的日志索引）。
            重新创建容器会丢弃旧日志，是最干净的方式。
        """
        container = ProcessService._get_container(client_id)
        if not container:
            return True, '日志已清空'

        # 容器存在则重新创建
        record = ProcessService._get_client_record(client_id)
        if not record:
            return False, '客户端不存在'

        image, version = ProcessService._resolve_image(record)
        ok, msg = ProcessService._run_container(client_id, image)
        if ok:
            ProcessService._write_back_version(client_id, image, version)
            return True, '日志已清空'

        return False, msg

    @staticmethod
    def remove_container(client_id):
        """停止并移除容器（删除客户端时调用）"""
        container = ProcessService._get_container(client_id)
        if not container:
            return True

        try:
            try:
                container.stop(timeout=10)
            except Exception:
                pass
            container.remove()
            ColorLogger.info('客户端 ' + str(client_id) + ' 容器已移除', 'Process')
            return True
        except APIError as e:
            ColorLogger.warning('移除容器 ' + str(client_id) + ' 失败: ' + str(e), 'Process')
            return False
