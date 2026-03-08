# 劳动用工管理系统 (Labor Management System)

一个基于 Flask 的劳动用工申请与审批管理系统，支持用工申请、审批、导出等功能。

## 功能特性

- **用户管理**：支持多用户、角色权限（管理员/普通用户）
- **用工申请**：在线填写用工申请单，支持 Excel 导入
- **工作项管理**：预定义工作项及用工系数
- **审批流程**：支持申请审批、审批意见填写
- **数据导出**：支持 PDF 格式导出
- **快照功能**：申请数据快照，防止基础数据变更影响历史记录

## 技术栈

| 组件 | 版本/技术 |
|------|----------|
| Python | 3.9.12 |
| Flask | 2.3.3 |
| SQLAlchemy | 2.0.23 |
| MySQL/MariaDB | - |
| 前端 | HTML5, CSS3, JavaScript |
| 部署 | Apache + mod_wsgi |

## 项目结构

```
labormanagement/
├── app.py                      # 主应用程序
├── config.py                   # 配置文件
├── models.py                   # 数据模型
├── init_tables.py              # 数据库初始化脚本
├── cache_config.py             # 缓存配置
├── rebulid.py                  # 重建脚本
├── download_static_resources.py # 静态资源下载
├── requirements.txt            # Python 依赖
├── labormanagement.wsgi        # WSGI 入口文件
├── templates/                  # HTML 模板
│   ├── base.html
│   ├── login.html
│   ├── change_password.html
│   ├── admin/
│   └── user/
├── static/                     # 静态资源
│   ├── css/
│   ├── js/
│   ├── fonts/
│   └── vendor/
├── uploads/                    # 上传文件目录
├── exports/                    # 导出文件目录
└── logs/                       # 日志目录
```

## 快速开始

### 1. 环境要求

- Python 3.9+
- MySQL 5.7+ 或 MariaDB 10.3+
- Apache 2.4+ (生产环境)

### 2. 安装依赖

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 配置

编辑 `config.py` 文件，修改数据库连接信息：

```python
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://用户名：密码@localhost:3306/数据库名'
SECRET_KEY = 'your-secret-key-here'
```

### 4. 初始化数据库

```bash
source venv/bin/activate
python init_tables.py
```

### 5. 开发环境运行

```bash
python app.py
# 访问 http://localhost:5000
```

### 6. 生产环境部署

参见 [生产环境部署手册](DEPLOYMENT.md)

## 默认账户

初始化后，系统会创建以下默认账户：

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |
| user1 | user123 | 普通用户 |

**首次登录后请及时修改密码！**

## 主要功能模块

### 用户管理
- 用户列表、新增、编辑、删除
- 角色分配（管理员/普通用户）
- 密码修改

### 用工申请
- 创建新的用工申请
- Excel 批量导入申请数据
- 查看申请详情
- 申请状态跟踪

### 工作项管理
- 工作项代码维护
- 用工系数配置
- 分类管理

### 审批管理
- 待审批列表
- 审批通过/驳回
- 审批意见填写
- 审批记录查询

## 配置说明

### config.py 配置项

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| SECRET_KEY | 安全密钥 | - |
| SQLALCHEMY_DATABASE_URI | 数据库连接 | - |
| SQLALCHEMY_TRACK_MODIFICATIONS | 追踪对象修改 | False |
| UPLOAD_FOLDER | 上传文件目录 | ./uploads |
| ALLOWED_EXTENSIONS | 允许上传的扩展名 | xlsx, xls |
| MAX_CONTENT_LENGTH | 最大上传大小 | 16MB |
| PDF_EXPORT_FOLDER | PDF 导出目录 | ./exports |

## 数据库表结构

| 表名 | 说明 |
|------|------|
| users | 用户表 |
| work_items | 工作项表 |
| labor_applications | 用工申请表 |
| application_items | 申请明细表 |

## 开发说明

### 添加新的工作项

可以通过以下方式添加工作项：

1. **后台管理界面**：登录后在管理界面添加
2. **Excel 导入**：使用模板批量导入
3. **数据库脚本**：直接执行 SQL 或 Python 脚本

### 修改用工系数

用工系数在工作项表中维护，修改后：
- 新申请使用新系数
- 历史申请使用快照数据（不受影响）

## 常见问题

### 数据库连接失败

检查 `config.py` 中的数据库连接配置，确保：
- 数据库服务已启动
- 用户名密码正确
- 用户有正确的访问权限

### 静态文件 404

检查 Apache 配置中的静态文件路径配置，确保 `Alias /static` 指向正确的目录。

### 上传文件失败

确保 `uploads` 目录存在且有写权限：

```bash
chown -R apache:apache uploads/
chmod 755 uploads/
```

## 日志

日志文件位于 `logs/` 目录：

- `app.log` - 应用程序日志
- `config.json` - 运行时配置

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0.0 | 2024-01 | 初始版本 |

## License

Copyright (c) 2024

## 联系方式

如有问题，请联系开发团队。
