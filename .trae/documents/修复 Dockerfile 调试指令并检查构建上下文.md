## 问题分析

本地文件存在，但容器内不存在。可能原因：

1. **GitHub Actions checkout 问题** - 可能没有正确拉取所有文件
2. **Docker 构建上下文问题** - 构建上下文可能不包含 lib 目录
3. **调试指令提前终止** - `&&` 连接时一个命令失败会导致整个 RUN 失败

## 修复方案

### 1. 修改 Dockerfile 调试指令（使用容错方式）

```dockerfile
# 调试：检查文件是否正确复制（容错版）
RUN echo "=== Checking frontend root ===" && \
    ls -la /app/frontend/ || true && \
    echo "=== Checking frontend src ===" && \
    ls -la /app/frontend/src/ || true && \
    echo "=== Checking frontend src/lib (if exists) ===" && \
    (ls -la /app/frontend/src/lib/ || echo "lib directory not found") && \
    echo "=== Checking frontend src/pages ===" && \
    ls -la /app/frontend/src/pages/ | head -20 || true
```

### 2. 修改 CI 配置，在构建前检查本地文件

在 CI 中添加步骤，确认文件在 GitHub Actions runner 上是否存在：

```yaml
- name: Check local files before build
  run: |
    echo "=== Checking local frontend files ==="
    ls -la frontend/src/
    ls -la frontend/src/lib/ || echo "lib directory not found locally"
```

## 确认后执行

请确认此计划，我将立即修改 Dockerfile 和 CI 配置。
