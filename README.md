# 劳动用工管理系统 (Labor Management System) v2.0

一个基于 **Flask + React** 的劳动用工申请与审批管理系统，采用前后端分离架构，支持用工申请、审批、导出等功能。

![License](https://img.shields.io/github/license/yourusername/labormanagement)
![Python](https://img.shields.io/badge/python-3.9-blue)
![Flask](https://img.shields.io/badge/Flask-2.3.3-green)
![React](https://img.shields.io/badge/React-18-blue)

## ✨ 特性

- **前后端分离**: RESTful API + React 前端
- **权限管理**: 基于角色的访问控制（管理员/普通用户）
- **数据安全**: 密码加密、SQL 注入防护、CORS 配置
- **数据快照**: 申请数据快照功能，防止基础数据变更影响历史记录
- **Excel 导入**: 支持批量导入工作项和申请数据
- **PDF 导出**: 支持申请单 PDF 格式导出
- **响应式设计**: 适配桌面和移动端

## 🏗️ 技术架构

### 后端
| 组件 | 版本/技术 |
|------|----------|
| 框架 | Flask 2.3.3 |
| ORM | SQLAlchemy 2.0.23 |
| 数据库 | MySQL 5.7+ / MariaDB 10.3+ |
| 认证 | Flask-Login |
| 部署 | Apache + mod_wsgi / Gunicorn |

### 前端
| 组件 | 版本/技术 |
|------|----------|
| 框架 | React 18 |
| 构建工具 | Vite 5 |
| UI 组件库 | Ant Design 5 |
| 状态管理 | Zustand |
| 路由 | React Router 6 |
| HTTP 客户端 | Axios |

## 📁 项目结构

```
labormanagement/
├── api/                        # 后端 API 模块
│   ├── __init__.py
│   ├── auth.py                # 认证 API
│   ├── users.py               # 用户管理 API
│   ├── work_items.py          # 工作项 API
│   ├── applications.py        # 申请 API
│   └── utils.py               # API 工具函数
├── frontend/                   # 前端 React 应用
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── database/                   # 数据库脚本
│   ├── init.sql               # 初始化 SQL
│   └── README.md
├── scripts/                    # 辅助脚本
│   ├── init_db.sh             # 数据库初始化
│   └── README.md
├── templates/                  # HTML 模板（传统模式）
├── static/                     # 静态资源
├── uploads/                    # 上传文件目录
├── exports/                    # 导出文件目录
├── logs/                       # 日志目录
├── app.py                      # Flask 应用主程序
├── config.py                   # 配置管理
├── models.py                   # 数据模型
├── manage.py                   # 管理命令
├── requirements.txt            # Python 依赖
├── .env.example                # 环境变量示例
└── README.md                   # 本文档
```

## 🚀 快速开始

### 后端服务

#### 1. 环境要求

- Python 3.9+
- MySQL 5.7+ 或 MariaDB 10.3+

#### 2. 安装依赖

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库连接等
```

#### 4. 初始化数据库

```bash
# 方式 1: 使用 SQL 脚本
mysql -u root -p < database/init.sql

# 方式 2: 使用管理命令
python manage.py init-db
```

#### 5. 启动服务

```bash
# 方式 1: 直接运行
python app.py

# 方式 2: 使用管理脚本
python manage.py runserver --debug

# 方式 3: 使用启动脚本
./run.sh  # Linux/Mac
run.bat   # Windows
```

访问 `http://localhost:5000`

### 前端服务

#### 1. 环境要求

- Node.js 18+
- npm 或 pnpm

#### 2. 安装依赖

```bash
cd frontend
npm install
```

#### 3. 配置环境

```bash
cp .env.example .env
# 编辑 .env 文件配置 API 地址
```

#### 4. 启动开发服务器

```bash
npm run dev
```

访问 `http://localhost:3000`

#### 5. 构建生产版本

```bash
npm run build
```

## 📋 API 接口

### 认证
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/login | 用户登录 |
| POST | /api/auth/logout | 用户登出 |
| GET | /api/auth/me | 获取当前用户 |
| POST | /api/auth/change-password | 修改密码 |

### 用户管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/users | 用户列表 |
| GET | /api/users/:id | 用户详情 |
| POST | /api/users | 创建用户 |
| PUT | /api/users/:id | 更新用户 |
| DELETE | /api/users/:id | 删除用户 |
| GET | /api/users/departments | 部门列表 |

### 工作项管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/work-items | 工作项列表 |
| GET | /api/work-items/:id | 工作项详情 |
| POST | /api/work-items | 创建工作项 |
| PUT | /api/work-items/:id | 更新工作项 |
| DELETE | /api/work-items/:id | 删除工作项 |
| GET | /api/work-items/categories | 分类列表 |
| POST | /api/work-items/import | 批量导入 |

### 用工申请
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/applications | 申请列表 |
| GET | /api/applications/:id | 申请详情 |
| POST | /api/applications | 创建申请 |
| PUT | /api/applications/:id | 更新申请 |
| DELETE | /api/applications/:id | 删除申请 |
| POST | /api/applications/:id/approve | 审批申请 |
| GET | /api/applications/stats | 统计数据 |

## 🔧 管理命令

```bash
# 查看可用命令
python manage.py --help

# 启动开发服务器
python manage.py runserver --debug

# 初始化数据库
python manage.py init-db

# 创建用户
python manage.py create-user

# 列出所有用户
python manage.py list-users

# 删除用户
python manage.py delete-user <用户名>

# 更新工作项系数
python manage.py update-coefficient <工作项代码>
```

## 🔐 默认账户

初始化后，系统会创建以下默认账户：

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |
| user1 | user123 | 普通用户 |

**⚠️ 首次登录后请立即修改默认密码！**

## 📖 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| FLASK_ENV | 运行环境 | development |
| SECRET_KEY | 安全密钥 | - |
| DATABASE_URL | 数据库连接 | - |
| LOG_LEVEL | 日志级别 | INFO |
| CORS_ORIGINS | 跨域来源 | http://localhost:3000 |

详见 `.env.example` 文件。

## 📦 生产环境部署

详见 [DEPLOYMENT.md](DEPLOYMENT.md)

### 后端部署

```bash
# 使用 Gunicorn
gunicorn app:app -w 4 -b 0.0.0.0:5000

# 或使用 Apache + mod_wsgi（参考 DEPLOYMENT.md）
```

### 前端部署

```bash
# 构建
npm run build

# 将 dist/ 目录部署到静态服务器或 CDN
```

## ❓ 常见问题

### 数据库连接失败
检查 `DATABASE_URL` 环境变量配置，确保数据库服务已启动且网络可达。

### CORS 错误
确保后端 `.env` 文件中 `CORS_ORIGINS` 配置包含前端地址。

### 静态文件 404
生产环境需配置静态文件服务，或使用前端构建工具打包后的资源。

## 📝 更新日志

详见 [CHANGELOG.md](CHANGELOG.md)

## 📄 License

MIT License - 详见 [LICENSE](LICENSE)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题，请联系开发团队。
