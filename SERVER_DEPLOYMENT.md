# 服务器部署说明 (CentOS 9 Stream)

## 环境要求

- Python 3.9.12+
- MariaDB 10.3+ (或 MySQL 5.7+)
- Apache 2.4+ (带 mod_wsgi) 或 Gunicorn

## 部署步骤

### 1. 拉取代码

```bash
cd /var/www/html
git clone <仓库 URL> labormanagement
cd labormanagement
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
vim .env  # 根据实际情况修改配置
```

**重要：数据库配置**

根据 MySQL/MariaDB 监听地址选择：

```ini
# IPv6 (CentOS 9 Stream 默认)
DATABASE_URL=mysql+pymysql://labor_app_user:labor_app_password@[::1]:3306/labor_application_db

# 或 IPv4
DATABASE_URL=mysql+pymysql://labor_app_user:labor_app_password@127.0.0.1:3306/labor_application_db
```

### 5. 初始化数据库

```bash
sudo mysql < database/init.sql
```

### 6. 设置目录权限

```bash
sudo chown -R apache:apache /var/www/html/labormanagement
sudo chmod 755 /var/www/html/labormanagement
sudo chmod 755 /var/www/html/labormanagement/uploads
sudo chmod 755 /var/www/html/labormanagement/exports
sudo chmod 755 /var/www/html/labormanagement/logs
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

### 8. 配置 SELinux 和防火墙

```bash
# SELinux
sudo setsebool -P httpd_can_network_connect 1
sudo setsebool -P httpd_read_user_content 1

# 防火墙
sudo firewall-cmd --permanent --add-port=9000/tcp
sudo firewall-cmd --reload
```

### 9. 启动服务

```bash
sudo systemctl restart httpd
sudo systemctl enable httpd
```

### 10. 验证部署

```bash
curl -I http://localhost:9000/api/health
```

访问 `http://<服务器 IP>:9000`

## 常用命令

```bash
# 查看服务状态
sudo systemctl status httpd

# 重启服务
sudo systemctl restart httpd

# 查看日志
sudo tail -f /var/log/httpd/labormanagement_error.log

# 进入虚拟环境
source venv/bin/activate

# 更新代码
git pull
```

## 注意事项

1. **Python 版本**: 服务器使用 Python 3.9，确保依赖包兼容
2. **数据库连接**: CentOS 9 Stream 默认使用 IPv6，确保 MySQL 用户有 IPv6 权限
3. **文件权限**: 确保 Apache 用户有读写权限
4. **安全**: 生产环境必须修改默认密码和 SECRET_KEY
