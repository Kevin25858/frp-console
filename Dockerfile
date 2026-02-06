# 多阶段构建 - 前端构建阶段
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# 设置环境变量
ENV NODE_ENV=production

# 复制前端依赖文件
COPY frontend/package*.json ./

# 安装前端依赖
RUN npm ci

# 复制前端源代码
COPY frontend/ ./

# 构建前端
RUN npm run build

# Python 后端阶段
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 复制 Python 依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 从前端构建阶段复制构建产物
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 复制应用代码
COPY app/ ./app/
COPY frpc/ ./frpc/

# 创建必要的目录
RUN mkdir -p clients data logs/frpc

# 设置环境变量
# 安全提示：ADMIN_PASSWORD 和 SECRET_KEY 必须通过环境变量传入，不要硬编码
ENV PYTHONUNBUFFERED=1 \
    PORT=7600

# 暴露端口
EXPOSE 7600

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7600/login')" || exit 1

# 启动应用
CMD ["python", "app/app.py"]
