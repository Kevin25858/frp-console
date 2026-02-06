# 贡献指南

感谢您对 FRP Console 项目的关注！我们欢迎各种形式的贡献，包括但不限于：

- 报告 Bug
- 提交功能建议
- 改进文档
- 提交代码修复或新功能
- 分享使用经验

## 🚀 如何贡献

### 报告问题

如果您发现了 Bug 或有功能建议，请通过 [GitHub Issues](https://github.com/yourusername/frp-console/issues) 提交。

提交问题时，请尽量提供以下信息：

- **问题描述**：清晰描述遇到的问题
- **复现步骤**：详细的操作步骤
- **期望行为**：您期望的结果
- **实际行为**：实际发生的结果
- **环境信息**：
  - 操作系统及版本
  - Python 版本
  - Node.js 版本
  - 浏览器类型及版本（如果是前端问题）
- **截图或日志**：如有错误信息请提供

### 提交代码

#### 开发环境设置

1. Fork 本仓库到您的 GitHub 账号

2. 克隆您的 Fork 到本地

```bash
git clone https://github.com/yourusername/frp-console.git
cd frp-console
```

3. 添加上游仓库

```bash
git remote add upstream https://github.com/originalowner/frp-console.git
```

4. 创建虚拟环境并安装依赖

```bash
# Python 后端
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖

# Node.js 前端
cd frontend
npm install
```

#### 开发流程

1. 创建功能分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/issue-description
```

2. 进行开发

   - 遵循现有的代码风格
   - 编写清晰的提交信息
   - 添加必要的测试
   - 更新相关文档

3. 运行测试

```bash
# 后端测试
pytest

# 前端测试
cd frontend
npm test
```

4. 提交更改

```bash
git add .
git commit -m "feat: 添加新功能描述"
```

5. 推送到您的 Fork

```bash
git push origin feature/your-feature-name
```

6. 创建 Pull Request

   - 在 GitHub 上创建 PR 到主仓库的 `main` 分支
   - 填写 PR 描述，说明更改内容和原因
   - 关联相关的 Issue（如果有）

#### 代码规范

##### Python 代码规范

- 遵循 [PEP 8](https://pep8.org/) 风格指南
- 使用 4 个空格缩进
- 最大行长度 100 字符
- 使用有意义的变量名
- 添加文档字符串（docstrings）

示例：

```python
def process_client_data(client_id: str, data: dict) -> bool:
    """
    处理客户端数据并更新状态。

    Args:
        client_id: 客户端唯一标识符
        data: 包含客户端信息的字典

    Returns:
        bool: 处理成功返回 True，否则返回 False
    """
    # 实现代码
    pass
```

##### TypeScript/React 代码规范

- 使用 TypeScript 严格模式
- 组件使用函数式组件和 Hooks
- 使用语义化的 HTML 标签
- 遵循 React 最佳实践

示例：

```typescript
interface ClientCardProps {
  clientId: string;
  name: string;
  status: 'online' | 'offline';
  onEdit: (id: string) => void;
}

export function ClientCard({ clientId, name, status, onEdit }: ClientCardProps) {
  return (
    <div className="client-card">
      <h3>{name}</h3>
      <span className={`status-${status}`}>{status}</span>
      <button onClick={() => onEdit(clientId)}>编辑</button>
    </div>
  );
}
```

##### 提交信息规范

我们使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型（type）**：

- `feat`: 新功能
- `fix`: 修复 Bug
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 代码重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

**示例**：

```
feat(api): 添加客户端批量删除功能

- 实现批量删除 API 端点
- 添加前端批量选择组件
- 更新相关测试

Closes #123
```

#### Pull Request 规范

- PR 标题应清晰描述更改内容
- 描述中说明更改的原因和影响
- 确保所有测试通过
- 确保代码符合项目规范
- 如有 UI 更改，请提供截图
- 一个 PR 应只解决一个问题或添加一个功能

### 文档贡献

文档是项目的重要组成部分，我们欢迎：

- 修正拼写或语法错误
- 改进文档清晰度
- 添加使用示例
- 翻译文档

文档位于 `docs/` 目录，使用 Markdown 格式。

## 🏗️ 项目结构

```
frp-console/
├── app/                    # 后端应用
│   ├── api/routes/        # API 路由
│   ├── services/          # 业务逻辑
│   ├── models/            # 数据模型
│   └── utils/             # 工具函数
├── frontend/              # 前端应用
│   ├── src/components/    # React 组件
│   ├── src/pages/         # 页面组件
│   └── src/lib/           # 工具库
├── tests/                 # 测试文件
├── docs/                  # 文档
└── frpc/                  # FRPC 相关文件
```

## 📝 开发指南

### 后端开发

- 使用 Flask 框架
- 遵循 RESTful API 设计原则
- 使用 SQLite 数据库
- 实现适当的错误处理

### 前端开发

- 使用 React 18 + TypeScript
- 使用 Tailwind CSS 进行样式设计
- 使用 shadcn/ui 组件库
- 使用 Vite 作为构建工具

### 测试

- 后端使用 pytest
- 前端使用 Vitest
- 保持测试覆盖率

## 💬 沟通渠道

- **GitHub Issues**: Bug 报告和功能建议
- **GitHub Discussions**: 一般性讨论和问题
- **Pull Requests**: 代码审查和技术讨论

## 🙏 感谢

再次感谢您的贡献！您的参与让这个项目变得更好。

## 📄 许可证

通过贡献代码，您同意您的贡献将在 MIT 许可证下发布。
