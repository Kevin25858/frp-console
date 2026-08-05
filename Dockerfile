# 多阶段构建 - 前端构建阶段
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npx vite build

# Python 后端阶段
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖 (systemd 提供 systemctl，通过 D-Bus 与宿主机通信)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl sudo dbus systemd && \
    rm -rf /var/lib/apt/lists/*

# 配置 sudoers 允许 appuser 执行 systemctl
COPY sudoers-frp-console /etc/sudoers.d/frp-console
RUN chmod 440 /etc/sudoers.d/frp-console

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制前端构建产物
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 复制应用代码
COPY app/ ./app/

# 创建非 root 用户，并加入 systemd-journal 组以读取日志
RUN groupadd -r appgroup && \
    groupadd -g 101 systemd-journal 2>/dev/null || true && \
    useradd -r -g appgroup -G systemd-journal -s /bin/false appuser

# 创建必要的目录并设置权限
RUN mkdir -p data logs && \
    chown -R appuser:appgroup /app && \
    chmod -R 755 /app

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    PORT=7600

EXPOSE 7600

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7600/login')" || exit 1

USER appuser

CMD ["python", "app/app.py"]
