# 开发者指南

## 开发环境设置

### 前提条件

- Python 3.12+
- Node.js 20+
- Git

### 后端开发

#### 安装依赖

```bash
pip install -r requirements.txt
```

#### 运行开发服务器

```bash
export ADMIN_PASSWORD=admin
python app/app.py
```

#### 代码结构

```
app/
├── api/                  # API 路由层
│   ├── routes/
│   │   ├── auth.py      # 认证路由
│   │   ├── clients.py   # 客户端路由
│   │   └── admin.py     # 管理员路由
│   └── __init__.py
├── services/            # 业务逻辑层
│   ├── auth_service.py
│   ├── client_service.py
│   ├── process_service.py
│   └── alert_service.py
├── models/              # 数据模型
│   ├── database.py
│   └── __init__.py
├── utils/               # 工具函数
│   ├── logger.py
│   ├── validators.py
│   ├── helpers.py
│   └── __init__.py
├── config.py            # 配置管理
└── app.py               # 应用入口
```

#### 添加新的 API 端点

1. 在 `app/api/routes/` 中创建或编辑路由文件
2. 使用装饰器 `@login_required` 和 `@csrf_required` 保护端点
3. 在服务层实现业务逻辑

示例：

```python
# app/api/routes/example.py
from flask import jsonify, request
from app.utils.decorators import login_required, csrf_required

@api_bp.route('/api/example', methods=['GET'])
@login_required
def get_example():
    return jsonify({'message': 'Hello'})

@api_bp.route('/api/example', methods=['POST'])
@login_required
@csrf_required
def create_example():
    data = request.json
    # 处理逻辑
    return jsonify({'success': True})
```

### 前端开发

#### 安装依赖

```bash
cd frontend
npm install
```

#### 运行开发服务器

```bash
npm run dev
```

#### 代码结构

```
frontend/src/
├── components/          # React 组件
│   ├── ui/             # shadcn/ui 组件
│   ├── layout.tsx      # 布局组件
│   ├── toaster.tsx     # Toast 通知
│   └── loading-spinner.tsx
├── pages/              # 页面组件
│   ├── dashboard.tsx
│   ├── clients/
│   │   ├── list.tsx
│   │   ├── add-client-dialog.tsx
│   │   └── edit-client-dialog.tsx
│   ├── settings.tsx
│   └── alerts.tsx
├── contexts/           # React Context
│   ├── auth-context.tsx
│   └── toast-context.tsx
├── hooks/              # 自定义 Hooks
│   └── useApi.ts
├── lib/                # 工具库
│   ├── api.ts          # API 请求工具
│   ├── utils.ts        # 工具函数
│   └── validations.ts  # Zod 验证模式
└── types/              # TypeScript 类型
    └── index.ts
```

#### 添加新组件

1. 在 `frontend/src/components/` 中创建组件文件
2. 使用 TypeScript 定义 props 类型
3. 导出组件供其他模块使用

示例：

```typescript
// frontend/src/components/example.tsx
interface ExampleProps {
  title: string;
  onClick?: () => void;
}

export function Example({ title, onClick }: ExampleProps) {
  return (
    <div className="p-4 border rounded">
      <h2>{title}</h2>
      <button onClick={onClick}>Click me</button>
    </div>
  );
}
```

#### 使用 API

```typescript
import { apiFetch } from '@/lib/api';

// GET 请求
const data = await apiFetch('/clients');

// POST 请求
await apiFetch('/clients', {
  method: 'POST',
  body: JSON.stringify({ name: 'test' }),
});

// PUT 请求
await apiFetch('/clients/1', {
  method: 'PUT',
  body: JSON.stringify({ name: 'updated' }),
});
```

#### 使用 Toast 通知

```typescript
import { useToast } from '@/contexts/toast-context';

function MyComponent() {
  const { toast } = useToast();

  const handleClick = () => {
    toast({
      title: "成功",
      description: "操作已完成",
      variant: "default"
    });
  };

  return <button onClick={handleClick}>Show Toast</button>;
}
```

### 代码规范

#### Python

- 使用 PEP 8 代码风格
- 添加类型注解
- 编写文档字符串

```python
def example_function(param: str) -> dict:
    """
    示例函数
    
    Args:
        param: 参数说明
        
    Returns:
        返回值说明
    """
    return {"result": param}
```

#### TypeScript/React

- 使用 TypeScript 严格模式
- 使用函数组件
- 遵循 React Hooks 规则
- 组件名使用 PascalCase
- 文件名使用 kebab-case

```typescript
interface Props {
  title: string;
}

export function MyComponent({ title }: Props) {
  const [count, setCount] = useState(0);

  return <div>{title}: {count}</div>;
}
```

### 测试

#### 后端测试

```bash
pip install pytest pytest-cov
pytest tests/
```

#### 前端测试

```bash
cd frontend
npm test
```

### 构建和部署

#### 构建前端

```bash
cd frontend
npm run build
```

#### Docker 构建

```bash
docker build -t frp-console .
```

#### Docker Compose 启动

```bash
docker-compose up -d
```

### 调试

#### 后端调试

使用 VS Code 的 Python 调试器或打印日志：

```python
from app.utils.logger import ColorLogger

ColorLogger.info("调试信息", "Debug")
```

#### 前端调试

使用浏览器 DevTools 或 React DevTools 扩展。

### 常见问题

**Q: 如何添加新的客户端类型？**

A: 在 `app/services/client_service.py` 中添加新的客户端类型处理逻辑，并在前端更新表单。

**Q: 如何修改主题颜色？**

A: 编辑 `frontend/index.css` 中的 CSS 变量。

**Q: 如何添加新的 API 端点？**

A: 在 `app/api/routes/` 中创建新的路由文件，并在 `app/api/routes/__init__.py` 中注册蓝图。

## 发布流程

1. 更新版本号
2. 更新 CHANGELOG.md
3. 运行测试
4. 构建前端
5. 打包发布

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

MIT License