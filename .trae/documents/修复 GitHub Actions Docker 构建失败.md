## 问题分析

本地 Docker 构建成功，但 GitHub Actions 上仍然失败。可能原因：

1. **Buildx 缓存问题** - CI 使用了 `docker/setup-buildx-action@v3`，可能有缓存
2. **Runner 环境问题** - GitHub Actions 的 runner 可能有不同的环境配置

## 修复方案

### 方案 1：禁用 Buildx 缓存（推荐先尝试）
修改 CI 配置，在 Build 任务中添加 `--no-cache` 并确保 Buildx 不使用缓存：

```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3
  with:
    driver-opts: network=host

- name: Build Docker image
  run: |
    docker buildx build --no-cache --load -t frp-console:test .
```

### 方案 2：添加调试信息
在构建步骤中添加更多调试信息，查看具体错误：

```yaml
- name: Build Docker image with debug
  run: |
    docker build --no-cache --progress=plain -t frp-console:test . 2>&1
```

### 方案 3：检查前端构建单独步骤
先单独测试前端构建是否正常：

```yaml
- name: Test frontend build
  working-directory: ./frontend
  run: |
    npm ci
    npx vite build
```

## 确认后执行
请确认此计划，我将立即修改 CI 配置并推送。