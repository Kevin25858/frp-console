## 问题分析

GitHub Actions 构建失败，错误信息：

```
Could not load /app/frontend/src/lib/api (imported by src/pages/dashboard.tsx): ENOENT: no such file or directory, open '/app/frontend/src/lib/api'
```

问题：Vite 在 Docker 中无法正确解析 `@/lib/api` 路径别名到 `api.ts` 文件。

## 修复方案

### 方案 1：修改 vite.config.ts，添加文件扩展名解析

配置 Vite 自动解析 `.ts` 扩展名。

### 方案 2：修改所有导入语句，添加 .ts 扩展名

将 `@/lib/api` 改为 `@/lib/api.ts`。

### 方案 3：使用 resolve.extensions 配置

添加 extensions 配置让 Vite 自动尝试解析 .ts 文件。

## 推荐方案

使用方案 3，在 vite.config.ts 中添加 extensions 配置：

```javascript
resolve: {
  alias: {
    "@": path.resolve(__dirname, "./src"),
  },
  extensions: ['.mjs', '.js', '.ts', '.jsx', '.tsx', '.json'],
},
```

## 需要修改的文件

1. `frontend/vite.config.ts` - 添加 extensions 配置

请
