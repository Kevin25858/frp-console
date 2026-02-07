## 需要修改的文件

### 1. app/config.py
修复 BASE_DIR 检测逻辑，确保在 host 网络模式下也能正确识别路径。

### 2. Dockerfile
- 安装 procps 包（提供 pgrep 命令）
- 确保 /opt/frp-console 目录结构正确

### 3. docker-compose.yml
- 添加 network_mode: host 选项
- 确保卷映射正确

### 4. 推送到 GitHub
将修复后的代码推送到 GitHub 仓库。

请确认这个计划后，我将开始执行修改。