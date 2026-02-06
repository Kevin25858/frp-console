## 问题分析

虽然添加了 `extensions` 配置，但 Vite 在 Docker 中仍然无法解析 `@/lib/api` 到 `api.ts`。

这是因为 `extensions` 配置主要对裸导入有效，对路径别名解析不完全有效。

## 修复方案

### 方案 1：修改所有导入语句，添加 .ts 扩展名

将 `@/lib/api` 改为 `@/lib/api.ts`

### 方案 2：使用 vite-tsconfig-paths 插件

安装并配置 vite-tsconfig-paths 插件来正确解析路径别名。

### 方案 3：修改 vite.config.ts，使用更精确的别名配置

## 推荐方案

使用方案 1，直接修改导入语句，这是最直接可靠的方案。

## 需要修改的文件

1. `frontend/src/pages/dashboard.tsx`
2. `frontend/src/pages/users.tsx`
3. `frontend/src/pages/alerts.tsx`
4. `frontend/src/pages/settings.tsx`
5. `frontend/src/pages/clients/list.tsx`
6. `frontend/src/pages/clients/add-client-dialog.tsx`
7. `frontend/src/pages/clients/edit-client-dialog.tsx`
8. `frontend/src/pages/clients/edit-config-dialog.tsx`
9. `frontend/src/pages/clients/view-config-dialog.tsx`
10. `frontend/src/hooks/useApi.ts`
11. `frontend/src/components/config-editor.tsx`

## 修改内容

将：

```typescript
import { apiFetch } from "@/lib/api";
```

改为：

```typescript
import { apiFetch } from "@/lib/api.ts";
```

请确认后我将开始执行修复。
