## 问题分析

Docker Hub (hub.docker.com) 在中国大陆访问受限，无法获取访问令牌。

## 解决方案：使用 GitHub Container Registry (ghcr.io)

GitHub 提供了免费的容器镜像仓库服务，可以直接使用，无需 Docker Hub。

### 修改内容

1. **修改 CI 配置**，将 Docker Hub 登录改为 GitHub Container Registry：
   - 使用 `ghcr.io` 作为镜像仓库
   - 使用 `GITHUB_TOKEN` 自动登录（无需额外配置 secrets）

2. **修改 Deploy 步骤**，从 ghcr.io 拉取镜像

### 修改后的 CI 配置

```yaml
- name: Login to GitHub Container Registry
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}

- name: Build and push Docker image
  uses: docker/build-push-action@v5
  with:
    context: .
    push: true
    tags: |
      ghcr.io/${{ github.repository_owner }}/frp-console:latest
      ghcr.io/${{ github.repository_owner }}/frp-console:${{ github.sha }}
```

### 优点
- ✅ 无需 Docker Hub 账号
- ✅ 无需手动配置登录凭证
- ✅ 国内访问速度更快
- ✅ 与 GitHub 集成更好

## 确认后执行

请确认此方案，我将立即修改 CI 配置。