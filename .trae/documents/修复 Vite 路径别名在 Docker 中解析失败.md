## 问题原因

Vite 的路径别名 `@/` 在 Docker Alpine Linux 环境中无法正确解析，导致构建失败。

错误信息：

```
Could not load /app/frontend/src/lib/api.ts (imported by src/pages/users.tsx)
```

## 修复方案

修改 `frontend/vite.config.ts`，使用 `URL` 和
