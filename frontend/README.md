# 劳动用工管理系统 - 前端

基于 React + Vite + Ant Design 的前端应用。

## 快速开始

### 1. 安装依赖

```bash
npm install
# 或
pnpm install
```

### 2. 配置环境

```bash
cp .env.example .env
# 编辑 .env 文件配置 API 地址
```

### 3. 启动开发服务器

```bash
npm run dev
# 访问 http://localhost:3000
```

### 4. 构建生产版本

```bash
npm run build
```

## 技术栈

- **框架**: React 18
- **构建工具**: Vite 5
- **UI 组件库**: Ant Design 5
- **状态管理**: Zustand
- **路由**: React Router 6
- **HTTP 客户端**: Axios
- **时间处理**: Day.js

## 项目结构

```
frontend/
├── src/
│   ├── api/           # API 请求模块
│   ├── assets/        # 静态资源
│   ├── components/    # 通用组件
│   ├── hooks/         # 自定义 Hooks
│   ├── layouts/       # 布局组件
│   ├── pages/         # 页面组件
│   ├── store/         # 状态管理
│   ├── utils/         # 工具函数
│   ├── App.jsx        # 应用根组件
│   └── main.jsx       # 应用入口
├── index.html
├── package.json
├── vite.config.js
└── .env.example
```

## API 接口

后端 API 地址配置在 `.env` 文件中：

```env
VITE_API_BASE_URL=http://localhost:5000/api
```

主要 API 端点：

- `POST /api/auth/login` - 用户登录
- `POST /api/auth/logout` - 用户登出
- `GET /api/users` - 用户列表
- `GET /api/work-items` - 工作项列表
- `GET /api/applications` - 申请列表
- `POST /api/applications` - 创建申请

## 开发规范

### 代码格式化

```bash
npm run lint
npm run format
```

### 提交规范

- `feat: 新功能`
- `fix: 修复 bug`
- `docs: 文档更新`
- `style: 代码格式调整`
- `refactor: 代码重构`
- `test: 测试相关`
- `chore: 构建/工具链相关`
