## 修复 CI/CD Backend Tests 失败

### 问题诊断
Backend Tests 在 Run tests 步骤失败，主要原因是测试依赖配置不完整。

### 修复步骤

#### 1. 更新 requirements.txt
添加缺失的测试依赖：
- pytest-flask
- flask-testing

#### 2. 修复 conftest.py
确保测试固件(fixtures)正确配置，避免导入错误。

#### 3. 更新 CI 工作流
确保 CI 环境正确设置 PYTHONPATH 以便 pytest 能发现 app 模块。

#### 4. 验证修复
本地运行测试确保通过。

#### 5. 推送修复到 GitHub
提交更改并推送到 main 分支，触发 CI 重新运行。

### 需要修改的文件
1. `/opt/frp-console-release/requirements.txt` - 添加测试依赖
2. `/opt/frp-console-release/tests/conftest.py` - 修复导入路径
3. `/opt/frp-console-release/.github/workflows/ci.yml` - 更新 CI 配置

请确认后我将开始执行修复。