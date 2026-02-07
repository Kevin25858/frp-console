#!/usr/bin/env python3
"""初始化 FRP Web Multi 数据库，导入示例客户端配置"""

import sqlite3
import os

DATABASE = '/opt/frp-console/data/frpc.db'
CONFIGS_DIR = '/opt/frp-console/clients'

# 确保目录存在
os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
os.makedirs(CONFIGS_DIR, exist_ok=True)

# 示例客户端配置（请替换为实际配置）
clients = [
    {
        'name': 'example-client-1',
        'config_path': '/opt/frp-console/clients/client-1.toml',
        'local_port': 8080,
        'remote_port': 8080,
        'server_addr': 'your-server-address'
    },
    {
        'name': 'example-client-2',
        'config_path': '/opt/frp-console/clients/client-2.toml',
        'local_port': 3000,
        'remote_port': 3000,
        'server_addr': 'your-server-address'
    }
]

# 初始化数据库
conn = sqlite3.connect(DATABASE)
c = conn.cursor()

# 创建表
c.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        config_path TEXT NOT NULL,
        local_port INTEGER,
        remote_port INTEGER,
        server_addr TEXT,
        status TEXT DEFAULT 'stopped',
        enabled BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        level TEXT,
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        alert_type TEXT,
        message TEXT,
        sent_to TEXT,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved BOOLEAN DEFAULT 0,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
''')

# 导入示例客户端
for client in clients:
    # 检查是否已存在
    existing = c.execute('SELECT id FROM clients WHERE name = ?', (client['name'],)).fetchone()
    if existing:
        print(f"客户端 {client['name']} 已存在，更新路径")
        c.execute('UPDATE clients SET config_path = ? WHERE name = ?',
                  (client['config_path'], client['name']))
        continue
    
    # 插入新客户端
    c.execute('''
        INSERT INTO clients (name, config_path, local_port, remote_port, server_addr, status)
        VALUES (?, ?, ?, ?, ?, 'stopped')
    ''', (client['name'], client['config_path'], client['local_port'], 
          client['remote_port'], client['server_addr']))
    
    print(f"✅ 已导入客户端: {client['name']}")

conn.commit()
conn.close()

print(f"\n🎉 数据库初始化完成！")
print(f"📊 共导入 {len(clients)} 个示例客户端")
print(f"💡 请访问 http://服务器IP:7600 管理您的 FRP 客户端")
