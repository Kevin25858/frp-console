## 问题分析

本地文件 `frontend/src/lib/api.ts` 确实存在，但 Docker 构建时提示找不到。可能原因：

1. **Docker COPY 指令问题** - 文件没有被正确复制到容器中
2. **路径解析问题** - Vite 的路径别名 `@/` 在容器中解析失败

## 修复方案

在 Dockerfile 的 `RUN npx vite build` 之前添加文件检查指令，确认文件是否被正确复制：

```dockerfile
# 复制前端源代码
COPY frontend/ ./

# 调试：检查文件是否存在
RUN ls -la /app/frontend/src/lib/ && \
    ls -la /app/frontend/src/pages/

# 构建前端
RUN npx vite build
```

这样可以确认：
1. `api.ts` 文件是否被正确复制到容器中
2. `alerts.tsx` 文件是否存在

## 确认后执行
请确认此计划，我将立即修改 Dockerfile 并推送。