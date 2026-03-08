# 服务器部署说明 (CentOS 9 Stream / MariaDB 10.11)

## 环境要求

- Python 3.9.12+
- MariaDB 10.3+ (或 MySQL 5.7+)
- Apache 2.4+ (带 mod_wsgi) 或 Gunicorn

---

## 📋 部署前检查

### 确认数据库已存在且有数据

```bash
mysql -u root -p labor_application_db -e "SHOW TABLES;"
```

预期输出：
```
+--------------------------------+
| Tables_in_labor_application_db |
+--------------------------------+
| application_items              |
| labor_applications             |
| users                          |
| work_items                     |
+--------------------------------+
```

✅ **如果表已存在，跳过数据库初始化步骤！**

### 确认数据库用户权限

```bash
mysql -u root -p -e "SHOW GRANTS FOR 'labor_app_user'@'localhost';"
mysql -u root -p -e "SHOW GRANTS FOR 'labor_app_user'@'127.0.0.1';"
```

确保用户有 `ALL PRIVILEGES` 权限。

### 确认 MariaDB 监听地址

```bash
# 查看 MariaDB 监听端口
sudo netstat -tlnp | grep mysql
# 或
sudo ss -tlnp | grep mysql
```

- 如果看到 `[::1]:3306` → 使用 IPv6 连接
- 如果看到 `127.0.0.1:3306` → 使用 IPv4 连接

---

## 🚀 部署步骤

### 1. 拉取代码

```bash
cd /var/www/html
git clone https://github.com/qianqianjie-999/labormanagement.git labormanagement
cd labormanagement
```

**更新已有部署：**
```bash
cd /var/www/html/labormanagement
git pull
```

### 2. 创建虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.server.example .env
vim .env
```

**`.env` 配置模板：**

```ini
# 运行环境
FLASK_ENV=production
FLASK_DEBUG=False

# 安全密钥（生产环境必须修改）
SECRET_KEY=your-production-secret-key-here

# 数据库配置
# IPv6 (CentOS 9 Stream 默认)
DATABASE_URL=mysql+pymysql://labor_app_user:labor_app_password@[::1]:3306/labor_application_db

# 或 IPv4（如果 MariaDB 监听 IPv4）
# DATABASE_URL=mysql+pymysql://labor_app_user:labor_app_password@127.0.0.1:3306/labor_application_db

# 日志配置
LOG_LEVEL=INFO
```

### 5. 初始化数据库 ⚠️

```bash
# ❌ 如果数据库已存在且有数据，跳过此步骤！
# sudo mysql < database/init.sql

# ✅ 仅当数据库为空或首次部署时执行
sudo mysql < database/init.sql
```

### 6. 设置目录权限

```bash
# 设置所有者（CentOS 9 使用 apache 用户）
sudo chown -R apache:apache /var/www/html/labormanagement

# 设置目录权限
sudo find /var/www/html/labormanagement -type d -exec chmod 755 {} \;

# 设置文件权限
sudo find /var/www/html/labormanagement -type f -exec chmod 644 {} \;

# 设置可执行文件权限
sudo chmod +x /var/www/html/labormanagement/manage.py
sudo chmod +x /var/www/html/labormanagement/run.sh

# 确保以下目录可写
sudo chmod 775 /var/www/html/labormanagement/uploads
sudo chmod 775 /var/www/html/labormanagement/exports
sudo chmod 775 /var/www/html/labormanagement/logs
```

### 7. 配置 Apache (使用 mod_wsgi)

创建 `/etc/httpd/conf.d/labormanagement.conf`:

```apache
Listen 9000

<VirtualHost *:9000>
    ServerName localhost
    DocumentRoot /var/www/html/labormanagement

    WSGIDaemonProcess labormanagement \
        python-path=/var/www/html/labormanagement \
        python-home=/var/www/html/labormanagement/venv

    WSGIProcessGroup labormanagement
    WSGIScriptAlias / /var/www/html/labormanagement/labormanagement.wsgi

    <Directory /var/www/html/labormanagement>
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

**重启 Apache 加载配置：**
```bash
sudo systemctl restart httpd
```

### 8. 配置 SELinux 和防火墙

```bash
# SELinux - 允许 Apache 访问网络
sudo setsebool -P httpd_can_network_connect 1

# SELinux - 允许 Apache 读取用户文件
sudo setsebool -P httpd_read_user_content 1

# 防火墙 - 开放端口
sudo firewall-cmd --permanent --add-port=9000/tcp
sudo firewall-cmd --reload
```

### 9. 测试数据库连接

```bash
source venv/bin/activate
python -c "
from app import create_app
from models import db, User
app = create_app()
with app.app_context():
    users = User.query.count()
    print(f'✅ 数据库连接成功！用户数：{users}')
"
```

### 10. 启动服务

```bash
# 重启 Apache
sudo systemctl restart httpd

# 设置开机自启
sudo systemctl enable httpd

# 查看服务状态
sudo systemctl status httpd
```

### 11. 验证部署

```bash
# 测试健康检查接口
curl -I http://localhost:9000/api/health

# 或直接访问
curl http://localhost:9000/login
```

访问 `http://<服务器 IP>:9000`

---

## 📝 常用命令

```bash
# 查看服务状态
sudo systemctl status httpd

# 重启服务
sudo systemctl restart httpd

# 停止服务
sudo systemctl stop httpd

# 查看日志
sudo tail -f /var/log/httpd/labormanagement_error.log

# 查看实时日志
sudo tail -f /var/log/httpd/labormanagement_error.log | grep -E "ERROR|WARNING"

# 进入虚拟环境
source venv/bin/activate

# 更新代码
cd /var/www/html/labormanagement
git pull
sudo systemctl restart httpd

# 备份数据库
mysqldump -u root -p labor_application_db > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复数据库
mysql -u root -p labor_application_db < backup_YYYYMMDD_HHMMSS.sql
```

---

## ⚠️ 注意事项

1. **Python 版本**: 服务器使用 Python 3.9，确保依赖包兼容
2. **数据库连接**: CentOS 9 Stream 默认使用 IPv6，确保 MySQL 用户有 IPv6 权限
3. **文件权限**: 确保 Apache 用户有读写权限
4. **安全**: 生产环境必须修改默认密码和 SECRET_KEY
5. **数据备份**: 定期备份数据库，防止数据丢失
6. **日志监控**: 定期检查错误日志，及时发现并解决问题

---

## 🔧 故障排查

### 数据库连接失败

```bash
# 测试数据库连接
mysql -u labor_app_user -p -h 127.0.0.1 labor_application_db
# 或 IPv6
mysql -u labor_app_user -p -h ::1 labor_application_db
```

### 权限问题

```bash
# 检查目录权限
ls -la /var/www/html/labormanagement

# 修复权限
sudo chown -R apache:apache /var/www/html/labormanagement
```

### 端口被占用

```bash
# 查看端口占用
sudo netstat -tlnp | grep 9000
sudo ss -tlnp | grep 9000

# 修改端口
sudo vim /etc/httpd/conf.d/labormanagement.conf  # 修改 Listen 端口
```

### 应用启动失败

```bash
# 手动测试应用
cd /var/www/html/labormanagement
source venv/bin/activate
python manage.py runserver

# 查看详细错误
sudo journalctl -u httpd -n 50 --no-pager
```
