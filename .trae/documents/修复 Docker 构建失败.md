## 修复 Docker Build 失败

### 问题分析
Docker 构建时 TypeScript 编译错误：
```
Cannot find module '@/lib/api' or its corresponding type declarations.
```

这是因为 TypeScript 在 Docker 构建环境中无法正确解析路径别名 `@/`。

### 修复方案

#### 方案 1：修改 Dockerfile 使用正确的构建命令
在 Dockerfile 中设置 NODE_ENV 并确保 TypeScript 能正确解析路径。

#### 方案 2：修改 tsconfig.app.json
确保路径别名配置正确，并包含所有必要的类型声明。

#### 方案 3：修改 vite.config.ts
确保在构建时路径别名能正确解析。

### 具体修改

1. **修改 Dockerfile** - 添加环境变量和构建优化
2. **修改 tsconfig.app.json** - 确保路径配置正确
3. **修改 vite.config.ts** - 确保构建时路径解析正确

### 预期结果
- Docker 构建能成功完成
- 前端静态文件正确生成
- Build 任务通过

请确认后我将开始执行修复。