# ============================================================
# FRP Console Dockerfile（多阶段构建，宿主机无需 Node/npm）
#   Stage 1: node 镜像编译前端（Vite build）
#   Stage 2: python 镜像运行后端，复用前端产物
# 只要宿主机装有 Docker，即可一键构建，无需预装任何工具链。
# ============================================================

# ==================== Stage 1: 构建前端 ====================
FROM node:20-alpine AS frontend-builder

WORKDIR /build

# 先只复制依赖清单，充分利用 Docker 层缓存
COPY frontend/package.json frontend/package-lock.json* ./

# 安装前端依赖（国内可用 registry 加速，可用 ARG 覆盖）
ARG NPM_REGISTRY=https://registry.npmjs.org
RUN npm config set registry $NPM_REGISTRY && \
    npm install --no-audit --no-fund

# 复制前端源码并构建
COPY frontend/ .

RUN npm run build

# ==================== Stage 2: 运行后端 ====================
FROM docker.m.daocloud.io/library/alpine:3.19

# 配置国内 apk 源（清华镜像，加速包下载）
RUN echo "https://mirrors.tuna.tsinghua.edu.cn/alpine/v3.19/main" > /etc/apk/repositories && \
    echo "https://mirrors.tuna.tsinghua.edu.cn/alpine/v3.19/community" >> /etc/apk/repositories

# 安装 Python 3 和 curl（curl 用于健康检查）
RUN apk add --no-cache python3 py3-pip curl

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖（清华 pip 源加速）
RUN pip3 install --no-cache-dir --break-system-packages \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r requirements.txt

# 从 Stage 1 复制前端构建产物（vite 默认输出到项目根 dist/）
COPY --from=frontend-builder /build/dist ./frontend/dist

# 复制后端应用代码
COPY app/ ./app/

# 创建非 root 用户（UID 1000，避开 alpine 默认占用的 999）
RUN adduser -D -u 1000 appuser && \
    mkdir -p data logs && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    PORT=7600

EXPOSE 7600

# 健康检查：访问 /login 返回 200 就算健康
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -sf http://localhost:7600/login || exit 1

# 切换到非 root 用户运行
USER appuser

# 启动命令
CMD ["python3", "app/app.py"]