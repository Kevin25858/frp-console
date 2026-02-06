## 问题分析

虽然 Dockerfile 已经改为 `npm install`，但构建仍然失败：
```
sh: vite: not found
```

## 可能原因

1. `node_modules/.bin` 没有在 PATH 中
2. npm 安装时出现了问题
3. 需要全局安装 vite

## 修复方案

修改 Dockerfile，使用以下方式之一：

### 方案 1：使用 npx 运行 vite（推荐）
```dockerfile
RUN npx vite build
```

### 方案 2：使用完整路径
```dockerfile
RUN ./node_modules/.bin/vite build
```

### 方案 3：全局安装 vite
```dockerfile
RUN npm install -g vite && vite build
```

## 推荐方案

使用方案 1（npx），因为它最可靠，会自动查找本地安装的 vite。

## 需要修改的文件

1. `/opt/frp-console-release/Dockerfile` - 修改构建命令

请确认后我将开始执行修复。