## 可能原因

1. **环境变量未生效** - 需要检查容器是否正确读取了 ADMIN_PASSWORD
2. **密码格式问题** - 纯数字可能被解析为数字而非字符串
3. **应用初始化问题** - 首次启动时可能使用了默认密码

## 排查步骤

### 1. 检查容器日志
```bash
docker logs frp-console
```

### 2. 检查环境变量是否正确设置
```bash
docker exec frp-console env | grep ADMIN
```

### 3. 尝试重启容器
```bash
docker restart frp-console
```

### 4. 如果仍有问题，删除容器重新创建（确保数据卷已挂载，不会丢失数据）
```bash
docker stop frp-console
docker rm frp-console
# 然后重新运行 docker run 命令
```

## 确认后执行

请确认此排查方案，或先执行步骤 1 和 2 查看输出结果。