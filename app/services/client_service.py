"""
客户端服务模块
处理客户端的增删改查操作（配置存在数据库，由 ProcessService 部署到容器）

为什么分 ClientService 和 ProcessService：
    单一职责原则：
      - ClientService 只管"数据库里的配置"（增删改查、校验）
      - ProcessService 只管"Docker 容器"（启动、停止、删除）
    这样修改配置不影响正在跑的容器，操作容器也不必动数据库。
    两者的桥梁是 client_id。

为什么用静态方法而不是普通方法：
    本项目不需要"客户端对象"这个概念（没有 Client 实例的状态需要保存），
    所有操作都是"给个 id，做某件事"，用静态方法更直接。
"""
import re

from utils.logger import ColorLogger
from utils.validators import validate_client_name, validate_toml_config
from models.database import get_db
from services.process_service import ProcessService


class ClientService:
    """客户端服务类 - 纯配置管理"""

    @staticmethod
    def get_all_clients():
        """获取所有客户端，返回字典列表"""
        db = get_db()
        # ORDER BY id 按创建顺序排序，符合直觉
        rows = db.execute('SELECT * FROM clients ORDER BY id').fetchall()

        # 把每行转成字典
        # sqlite3.Row 对象不能直接 JSON 序列化，转成 dict 才能返回给前端
        result = []
        for row in rows:
            result.append(dict(row))
        return result

    @staticmethod
    def get_client(client_id):
        """获取单个客户端，返回字典或 None"""
        db = get_db()
        # 用 ? 占位符而不是字符串拼接，防止 SQL 注入
        # 攻击者如果在 client_id 里塞 "1 OR 1=1" 会很危险
        row = db.execute(
            'SELECT * FROM clients WHERE id = ?', (client_id,)
        ).fetchone()

        if row:
            return dict(row)
        return None

    @staticmethod
    def _parse_display_fields(config_content):
        """
        从配置内容中解析出服务器地址、本地端口、远程端口
        用于在列表中展示

        为什么要把这些字段单独存到数据库：
            1. 列表页要显示这些信息，如果每次都解析 TOML 会慢
            2. 可以用 SQL 直接按端口/地址筛选
            3. 解析一次存起来，编辑配置时同步更新即可

        返回:
            (服务器地址, 本地端口, 远程端口)
        """
        server_addr = ''
        local_port = 0
        remote_port = 0

        try:
            # 尝试用 TOML 解析器解析
            # Python 3.11+ 自带 tomllib，低版本需要装 tomli
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib

            parsed = tomllib.loads(config_content)

            # 获取服务器地址（兼容多种写法）
            # frpc 配置有两种风格：
            #   新版：[common] 节里写 serverAddr
            #   旧版：顶层直接写 server_addr
            # 这里都兼容
            common = parsed.get('common', {})
            server_addr = common.get('serverAddr')
            if not server_addr:
                server_addr = common.get('server_addr')
            if not server_addr:
                server_addr = parsed.get('serverAddr')
            if not server_addr:
                server_addr = parsed.get('server_addr')
            if not server_addr:
                server_addr = ''

            # 获取代理的端口信息
            proxies = parsed.get('proxies', [])
            if isinstance(proxies, list) and len(proxies) > 0:
                # 新版格式：[[proxies]] 是数组
                # 只取第一个代理的端口（列表展示够用了）
                proxy = proxies[0]
                local_port = proxy.get('localPort')
                if not local_port:
                    local_port = proxy.get('local_port')
                if not local_port:
                    local_port = 0

                remote_port = proxy.get('remotePort')
                if not remote_port:
                    remote_port = proxy.get('remote_port')
                if not remote_port:
                    remote_port = 0
            else:
                # 旧版格式：[proxy] 是单数
                proxy = parsed.get('proxy', {})
                if isinstance(proxy, dict):
                    local_port = proxy.get('localPort')
                    if not local_port:
                        local_port = proxy.get('local_port')
                    if not local_port:
                        local_port = 0

                    remote_port = proxy.get('remotePort')
                    if not remote_port:
                        remote_port = proxy.get('remote_port')
                    if not remote_port:
                        remote_port = 0

        except Exception as e:
            # TOML 解析失败，用正则表达式兜底
            # 这是为了应对"用户手写的配置格式不标准"的情况
            # 至少能从文本里抠出关键字段
            ColorLogger.warning('解析 TOML 配置失败，使用正则回退: ' + str(e), 'Client')

            # 正则解释：
            #   server_addr|serverAddr  匹配任一字段名
            #   \s*=\s*                 匹配 = 号（两边可能有空格）
            #   ["\']?                  引号可选
            #   ([^"\'\n]+)             捕获组：非引号非换行的字符
            addr_match = re.search(r'server_addr|serverAddr\s*=\s*["\']?([^"\'\n]+)["\']?', config_content)
            local_match = re.search(r'local_port|localPort\s*=\s*(\d+)', config_content)
            remote_match = re.search(r'remote_port|remotePort\s*=\s*(\d+)', config_content)

            if addr_match:
                server_addr = addr_match.group(1).strip()
            if local_match:
                local_port = int(local_match.group(1))
            if remote_match:
                remote_port = int(remote_match.group(1))

        return server_addr, int(local_port or 0), int(remote_port or 0)

    @staticmethod
    def _generate_toml(data):
        """
        根据表单字段生成 frpc TOML 配置（兼容 frpc v0.52+）

        为什么不让用户直接写 TOML：
            初学者可能不熟悉 TOML 格式，提供表单填写更友好。
            高级用户可以在创建后编辑原始配置。

        为什么用字符串拼接而不是 toml 库序列化：
            1. 控制字段顺序，方便阅读
            2. 避免引入额外依赖
            3. 生成的配置量小，拼接更直观
        """
        server_addr = data.get('server_addr', '')
        server_port = int(data.get('server_port', 7000) or 7000)
        user = data.get('user', '')
        token = data.get('token', '')

        # 代理名称，默认用 'proxy'
        # 如果没填就用客户端名称，都没填就用 'proxy'
        proxy_name = data.get('proxy_name')
        if not proxy_name:
            proxy_name = data.get('name')
        if not proxy_name:
            proxy_name = 'proxy'

        local_port = int(data.get('local_port', 0) or 0)
        remote_port = int(data.get('remote_port', 0) or 0)

        # 逐行拼接 TOML 配置
        # loginFailExit = false：连不上服务器不退出，方便调试
        lines = []
        lines.append('serverAddr = "' + server_addr + '"')
        lines.append('serverPort = ' + str(server_port))
        if user:
            lines.append('user = "' + user + '"')
        lines.append('loginFailExit = false')

        if token:
            # [auth] 节单独放，token 鉴权
            lines.append('')
            lines.append('[auth]')
            lines.append('method = "token"')
            lines.append('token = "' + token + '"')

        # [[proxies]] 是数组节，表示一个代理
        lines.append('')
        lines.append('[[proxies]]')
        lines.append('name = "' + proxy_name + '"')
        lines.append('type = "tcp"')
        lines.append('localIP = "127.0.0.1"')
        lines.append('localPort = ' + str(local_port))
        lines.append('remotePort = ' + str(remote_port))
        # 加密和压缩提升安全性和传输效率
        lines.append('transport.useEncryption = true')
        lines.append('transport.useCompression = true')

        return '\n'.join(lines) + '\n'

    @staticmethod
    def create_client(data):
        """创建新客户端"""
        name = data.get('name')
        # 先验证名称合法性
        valid, message = validate_client_name(name)
        if not valid:
            return False, {'error': message}

        # 两种模式：粘贴配置 或 表单生成
        # 用户可以两种方式创建：
        #   1. 直接粘贴现成的 TOML 配置
        #   2. 填表单，由系统生成 TOML
        if data.get('config_content'):
            # 粘贴配置模式
            config_content = data.get('config_content')
            # 校验 TOML 格式正确
            valid, message = validate_toml_config(config_content)
            if not valid:
                return False, {'error': message}

            # 从配置里解析出展示字段
            server_addr, local_port, remote_port = ClientService._parse_display_fields(config_content)
            token = data.get('token', '')
            user = data.get('user', '')
        else:
            # 表单生成模式
            server_addr = data.get('server_addr', '')
            token = data.get('token', '')
            user = data.get('user', '')
            local_port = data.get('local_port', 0)
            remote_port = data.get('remote_port', 0)
            config_content = ClientService._generate_toml(data)

            # 校验生成的配置（防止用户输入非法值）
            valid, message = validate_toml_config(config_content)
            if not valid:
                return False, {'error': message}

        # 可选字段：frp 版本和自定义镜像
        # 没传就是 None，启动容器时会用默认值
        frp_version = data.get('frp_version')
        if not frp_version:
            frp_version = None

        image = data.get('image')
        if not image:
            image = None

        # 写入数据库
        db = get_db()
        server_port = data.get('server_port', 7000) or 7000
        cursor = db.execute('''
            INSERT INTO clients (name, config_content, local_port, remote_port, server_addr, server_port, token, user, enabled, frp_version, image, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, 'stopped')
        ''', (name, config_content, local_port, remote_port, server_addr,
              server_port, token, user, frp_version, image))
        db.commit()
        # lastrowid 是新插入记录的自增 ID
        client_id = cursor.lastrowid

        ColorLogger.success('客户端 ' + name + ' 创建成功', 'Client')
        return True, {'id': client_id, 'message': '创建成功'}

    @staticmethod
    def update_client(client_id, data):
        """更新客户端信息"""
        db = get_db()
        client = db.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
        if client is None:
            return False, {'error': '客户端不存在'}

        # 获取新值，如果没有传就用旧值
        # data.get(key, default) 的 default 是"键不存在"时的默认值
        # 这里用数据库里的旧值作为默认，实现"部分更新"
        name = data.get('name', client['name'])
        enabled = data.get('enabled', client['enabled'])
        local_port = data.get('local_port', client['local_port'])
        remote_port = data.get('remote_port', client['remote_port'])
        server_addr = data.get('server_addr', client['server_addr'])
        server_port = data.get('server_port', client['server_port'])
        token = data.get('token', client['token'])
        user = data.get('user', client['user'])

        # frp_version 和 image 只在明确传入时才更新
        # 用 'key' in data 判断"是否传入"，避免被误置为 None
        if 'frp_version' in data:
            frp_version = data['frp_version']
        else:
            frp_version = client['frp_version']

        if 'image' in data:
            image = data['image']
        else:
            image = client['image']

        # 如果改了名字，需要验证
        # 没改就不用验证，省一次校验
        if name != client['name']:
            valid, message = validate_client_name(name)
            if not valid:
                return False, {'error': message}

        # enabled 转成 0 或 1
        # SQLite 没有真正的布尔类型，用 0/1 表示
        enabled_value = 1
        if not enabled:
            enabled_value = 0

        db.execute('''
            UPDATE clients SET name = ?, enabled = ?, local_port = ?, remote_port = ?,
            server_addr = ?, server_port = ?, token = ?, user = ?, frp_version = ?, image = ?,
            updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (name, enabled_value, local_port, remote_port, server_addr,
              server_port, token, user, frp_version, image, client_id))
        db.commit()

        ColorLogger.info('客户端 ' + name + ' 更新成功', 'Client')
        return True, {'message': '更新成功'}

    @staticmethod
    def delete_client(client_id):
        """删除客户端（同时移除容器和配置文件）"""
        db = get_db()
        client = db.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
        if client is None:
            return False, {'error': '客户端不存在'}

        # 先移除容器和配置文件
        # 顺序很重要：先清理外部资源，再删数据库记录
        # 如果反过来，删完数据库记录后清理失败，会留下孤儿容器
        ProcessService.remove_container(client_id)
        ProcessService.remove_config(client_id)

        # 再删除数据库记录
        db.execute('DELETE FROM clients WHERE id = ?', (client_id,))
        db.commit()

        ColorLogger.success('客户端 ' + client['name'] + ' 删除成功', 'Client')
        return True, {'message': '删除成功'}

    @staticmethod
    def get_client_config(client_id):
        """获取客户端配置文件内容"""
        client = ClientService.get_client(client_id)
        if client is None:
            return False, {'error': '客户端不存在'}

        config = client.get('config_content', '')
        return True, {'config': config}

    @staticmethod
    def update_client_config(client_id, config_content):
        """更新客户端配置文件内容"""
        client = ClientService.get_client(client_id)
        if client is None:
            return False, {'error': '客户端不存在'}

        # 验证配置格式
        # 不允许存入非法 TOML，避免后续启动容器失败
        valid, message = validate_toml_config(config_content)
        if not valid:
            return False, {'error': message}

        # 同步展示字段（服务器地址、端口等）
        # 配置改了，列表展示的字段也要跟着更新
        server_addr, local_port, remote_port = ClientService._parse_display_fields(config_content)

        db = get_db()
        db.execute('''
            UPDATE clients SET config_content = ?, server_addr = ?, local_port = ?, remote_port = ?,
            updated_at = CURRENT_TIMESTAMP WHERE id = ?
        ''', (config_content, server_addr, local_port, remote_port, client_id))
        db.commit()

        ColorLogger.success('客户端 ' + client['name'] + ' 配置更新成功', 'Client')
        return True, {'message': '配置更新成功'}
