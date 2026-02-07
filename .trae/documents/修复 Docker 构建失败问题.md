## 问题原因
Docker 构建在 `RUN npx vite build` 步骤失败，原因是 `frontend/src/i18n/index.ts` 中的导入缺少文件扩展名：

```typescript
import zh from './locales/zh';   // ❌ 缺少 .ts 扩展名
import en from './locales/en';   // ❌ 缺少 .ts 扩展名
```

## 修复步骤

### 1. 修复 i18n/index.ts（关键修复）
添加文件扩展名：
```typescript
import zh from './locales/zh.ts';
import en from './locales/en.ts';
```

### 2. 可选：修复其他相对路径导入（为了一致性）
- `frontend/src/components/layout.tsx`
- `frontend/src/components/protected-route.tsx`
- `frontend/src/pages/clients/list.tsx`

### 3. 本地验证
运行 `docker build` 验证修复是否成功。

## 确认后执行
请确认此计划，我将立即执行修复。