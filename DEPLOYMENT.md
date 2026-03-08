# 生产环境部署手册

本手册记录了"劳动用工管理系统"在 CentOS Stream 服务器上，通过 **Apache + mod_wsgi** 架构部署至生产环境的完整流程。

## 一、部署概述

### 架构选择

- **最终架构**: Apache (httpd) + mod_wsgi
- **核心原则**: 确保生产环境（Apache 进程）与开发环境隔离

### 系统要求

| 组件 | 要求 |
|------|------|
| 操作系统 | CentOS 9 Stream |
| Python | 3.9.12+ |
| 数据库 | MySQL 5.7+ 或 MariaDB 10.3+ |
| Web 服务器 | Apache 2.4+ |

## 二、部署前准备

### 1. 项目放置与权限

```bash
# 项目主目录
sudo mkdir -p /var/www/html/labormanagement
sudo cp -r /path/to/project/* /var/www/html/labormanagement/

# 设置权限
sudo chown -R apache:apache /var/www/html/labormanagement
sudo chmod 755 /var/www/html/labormanagement
```

### 2. 创建 Python 虚拟环境

```bash
cd /var/www/html/labormanagement
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
# 解决 numpy 与 pandas 兼容性问题
pip install numpy==1.24.3 pandas==1.5.3

# 安装其他依赖
pip install -r requirements.txt
```

## 三、配置 Apache 与 mod_wsgi

### 1. 安装 mod_wsgi

```bash
# 安装 EPEL 源
sudo dnf install epel-release -y

# 安装 mod_wsgi
sudo dnf install mod_wsgi -y
```

### 2. 配置 WSGI 入口文件

确保 `labormanagement.wsgi` 文件内容正确：

```python
#!/usr/bin/python3.9
import sys
import logging
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, '/var/www/html/labormanagement')
from app import create_app
application = create_app()
```

### 3. 配置 Apache 虚拟主机

创建 `/etc/httpd/conf.d/labormanagement.conf`:

```apache
Listen 9000

<VirtualHost *:9000>
    ServerName localhost
    ServerAdmin admin@example.com

    WSGIDaemonProcess labormanagement python-path=/var/www/html/labormanagement python-home=/var/www/html/labormanagement/venv
    WSGIProcessGroup labormanagement
    WSGIScriptAlias / /var/www/html/labormanagement/labormanagement.wsgi

    <Directory /var/www/html/labormanagement>
        WSGIProcessGroup labormanagement
        WSGIApplicationGroup %{GLOBAL}
        Require all granted
    </Directory>

    Alias /static /var/www/html/labormanagement/static
    <Directory /var/www/html/labormanagement/static>
        Require all granted
    </Directory>

    ErrorLog /var/log/httpd/labormanagement_error.log
    CustomLog /var/log/httpd/labormanagement_access.log combined
</VirtualHost>
```

### 4. 重启 Apache

```bash
sudo systemctl restart httpd
sudo systemctl enable httpd
```

## 四、配置系统策略与防火墙

### 1. SELinux 配置

```bash
# 允许 Apache 进行网络连接
sudo setsebool -P httpd_can_network_connect 1

# 允许 Apache 读取用户内容
sudo setsebool -P httpd_read_user_content 1

# 设置文件上下文 (如需要)
sudo semanage fcontext -a -t httpd_sys_content_t "/var/www/html/labormanagement(/.*)?"
sudo restorecon -R /var/www/html/labormanagement
```

### 2. 防火墙配置

```bash
# 开放 9000 端口
sudo firewall-cmd --permanent --add-port=9000/tcp
sudo firewall-cmd --reload

# 验证
sudo firewall-cmd --list-ports
```

## 五、数据库配置

### 1. 创建数据库

```sql
CREATE DATABASE labor_application_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 创建数据库用户

```sql
-- 为 IPv4 连接创建用户
CREATE USER 'labor_app_user'@'127.0.0.1' IDENTIFIED BY 'labor_app_password';
GRANT ALL PRIVILEGES ON labor_application_db.* TO 'labor_app_user'@'127.0.0.1';

-- 为 IPv6 连接创建用户 (防止 ::1 连接问题)
CREATE USER 'labor_app_user'@'::1' IDENTIFIED BY 'labor_app_password';
GRANT ALL PRIVILEGES ON labor_application_db.* TO 'labor_app_user'@'::1';

-- 本地连接
CREATE USER 'labor_app_user'@'localhost' IDENTIFIED BY 'labor_app_password';
GRANT ALL PRIVILEGES ON labor_application_db.* TO 'labor_app_user'@'localhost';

FLUSH PRIVILEGES;
```

### 3. 修改应用配置

编辑 `/var/www/html/labormanagement/config.py`:

```python
# 推荐使用 IPv4 地址避免 ::1 问题
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://labor_app_user:labor_app_password@127.0.0.1:3306/labor_application_db'
```

## 六、初始化数据库

**重要**: 必须以 apache 用户身份执行初始化脚本！

```bash
cd /var/www/html/labormanagement
sudo -u apache /var/www/html/labormanagement/venv/bin/python /var/www/html/labormanagement/init_tables.py
```

预期输出:
```
✅ 模块导入成功
✅ 数据库表创建成功！
📊 已创建的表：['application_items', 'labor_applications', 'users', 'work_items']
👤 现有用户数量：0
✅ 默认用户创建完成
   管理员：admin / admin123
   普通用户：user1 / user123
✅ 示例工作项数据插入成功
🎉 数据库完全初始化完成！
```

## 七、验证部署

### 1. 检查服务状态

```bash
# 检查端口监听
sudo ss -tlnp | grep :9000

# 检查 Apache 状态
sudo systemctl status httpd
```

### 2. 测试应用响应

```bash
curl -I http://localhost:9000/login
```

返回 `200 OK` 或 `302 Found` 表示成功。

### 3. 浏览器访问

访问 `http://<服务器 IP>:9000`

使用默认账户登录:
- 管理员：`admin` / `admin123`
- 普通用户：`user1` / `user123`

## 八、日常维护

### 常用命令

| 操作 | 命令 |
|------|------|
| 重启应用 | `sudo systemctl restart httpd` |
| 查看错误日志 | `sudo tail -f /var/log/httpd/labormanagement_error.log` |
| 查看访问日志 | `sudo tail -f /var/log/httpd/labormanagement_access.log` |
| 检查进程 | `ps aux \| grep httpd` |

### 日志文件位置

- 错误日志：`/var/log/httpd/labormanagement_error.log`
- 访问日志：`/var/log/httpd/labormanagement_access.log`
- 应用日志：`/var/www/html/labormanagement/logs/`

## 九、常见问题排查

### 1. IndentationError in WSGI file

**症状**: Apache 启动失败，日志显示缩进错误

**解决**: 确保 `.wsgi` 文件没有多余缩进或语法错误

### 2. ModuleNotFoundError

**症状**: 应用无法加载，提示模块找不到

**解决**:
```bash
# 确认虚拟环境中已安装包
source venv/bin/activate
pip list

# 检查 Apache 配置中的 python-home 路径
```

### 3. 数据库连接被拒绝

**症状**: `Access denied for user 'labor_app_user'@'::1'`

**解决**:
1. 检查用户密码是否正确
2. 为用户添加 IPv6 权限（见数据库配置部分）
3. 或在 config.py 中使用 `127.0.0.1` 而非 `localhost`

### 4. Table doesn't exist

**症状**: `Table 'labor_application_db.users' doesn't exist`

**解决**: 以 apache 用户身份执行初始化脚本
```bash
sudo -u apache /var/www/html/labormanagement/venv/bin/python /var/www/html/labormanagement/init_tables.py
```

### 5. 静态文件 404

**症状**: CSS/JS/图片等资源无法加载

**解决**: 检查 Apache 配置中的 `Alias /static` 指令及对应目录权限

### 6. Permission Denied

**症状**: 上传文件或导出 PDF 时权限错误

**解决**:
```bash
sudo chown -R apache:apache /var/www/html/labormanagement/uploads
sudo chown -R apache:apache /var/www/html/labormanagement/exports
sudo chmod 755 /var/www/html/labormanagement/uploads
sudo chmod 755 /var/www/html/labormanagement/exports
```

## 十、更新部署

当需要更新代码时:

```bash
# 1. 进入项目目录
cd /var/www/html/labormanagement

# 2. 备份当前版本 (可选)
sudo cp -r . /backup/labormanagement_$(date +%Y%m%d)

# 3. 拉取或复制新代码
# git pull (如使用 Git)
# 或 cp -r /path/to/new/* .

# 4. 更新依赖 (如需要)
source venv/bin/activate
pip install -r requirements.txt

# 5. 重启 Apache
sudo systemctl restart httpd
```

## 十一、安全建议

1. **修改默认密码**: 首次登录后立即修改默认账户密码
2. **定期备份**: 定期备份数据库和应用文件
3. **日志监控**: 定期检查错误日志和访问日志
4. **更新依赖**: 定期检查并更新 Python 依赖包
5. **限制访问**: 如可能，配置 IP 白名单或内网访问
