# 数据库脚本目录

包含所有与数据库相关的 SQL 脚本和迁移文件。

## 文件说明

| 文件 | 说明 |
|------|------|
| `init.sql` | 数据库初始化脚本，包含建表、初始数据等 |
| `migrations/` | 数据库迁移脚本（版本更新时使用） |
| `seeds/` | 种子数据脚本（测试数据） |

## 使用方法

### 1. 初始化数据库

```bash
# 登录 MySQL
mysql -u root -p

# 执行初始化脚本
source database/init.sql
```

或者一行命令：

```bash
mysql -u root -p < database/init.sql
```

### 2. 创建数据库迁移

当需要修改数据库结构时，创建新的迁移文件：

```bash
# 命名格式：V{版本号}_{描述}.sql
# 例如：V1.1.0_add_user_phone.sql
```

### 3. 数据库备份

```bash
# 备份整个数据库
mysqldump -u labor_app_user -p labor_application_db > backup_$(date +%Y%m%d).sql

# 恢复数据库
mysql -u labor_app_user -p labor_application_db < backup_20240101.sql
```

## 数据库表关系

```
users (用户表)
  └── labor_applications (用工申请表)
        └── application_items (申请明细表)
              └── work_items (工作项表)
```

## 注意事项

1. 生产环境执行 SQL 前先备份数据
2. 迁移脚本需要保证幂等性（可重复执行）
3. 敏感数据（如密码）使用占位符，由应用程序生成
