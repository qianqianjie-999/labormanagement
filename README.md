根据您提供的六个对话记录，我已将其整理为一份完整的《劳动用工管理系统生产环境部署手册》。这份文档系统地总结了整个部署流程、关键决策、故障排查点以及最终的成功配置。

---

## 📖 劳动用工管理系统生产环境部署手册

本手册记录了“劳动用工管理系统”在 CentOS Stream 服务器上，通过 **Apache + mod_wsgi** 架构成功部署至生产环境的完整流程、关键问题与解决方案。

### 一、 部署概述与架构决策

*   **最终架构**：Apache (httpd) + mod_wsgi
*   **放弃的架构**：Nginx + uWSGI + Unix Socket
*   **决策原因**：原方案在配置 `mod_proxy_uwsgi` 时遇到语法兼容性问题。切换为与服务器上已稳定运行的其他项目（`signal_fault`）一致的 `mod_wsgi` 架构，路径更直接，避开了代理配置的复杂性。
*   **核心原则**：确保生产环境（Apache 进程）的操作（如创建数据库表）必须与开发环境（直接运行 `app.py`）隔离，使用完全相同的用户、Python环境和应用配置上下文执行。

### 二、 部署前准备

1.  **项目放置与权限**：
    *   项目主目录：`/var/www/html/labormanagement`
    *   权限设置：确保 Apache 用户有权访问。
        ```bash
        sudo chown -R apache:apache /var/www/html/labormanagement
        ```
2.  **Python 虚拟环境**：
    *   在项目目录内创建并激活虚拟环境。
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

### 三、 详细部署步骤

#### 步骤 1：解决依赖冲突
部署初期遇到核心依赖 `numpy` 与 `pandas` 的二进制不兼容问题。
*   **解决方案**：降级到稳定的版本组合。
    ```bash
    pip install numpy==1.24.3 pandas==1.5.3
    ```
*   **后续操作**：安装其他项目依赖 (`Flask`, `Flask-SQLAlchemy`, `pymysql` 等)。

#### 步骤 2：配置 Apache 与 mod_wsgi
这是确保应用能被 Apache 加载的关键。
1.  **创建正确的 WSGI 入口文件** (`labormanagement.wsgi`)。
    *   **核心要点**：文件必须语法正确，无多余缩进或注释掉的代码行。
    *   **正确内容**：
        ```python
        #!/usr/bin/python3.9
        import sys
        import logging
        logging.basicConfig(stream=sys.stderr)
        sys.path.insert(0, '/var/www/html/labormanagement')
        from app import create_app
        application = create_app()
        ```
2.  **配置 Apache 虚拟主机**。
    *   在 `/etc/httpd/conf.d/` 下创建配置文件（如 `labormanagement.conf`）。
    *   **关键配置项**：
        *   `Listen 9000`：指定应用监听端口。
        *   `WSGIDaemonProcess` 和 `WSGIProcessGroup`：正确指向项目路径和虚拟环境。
        *   `WSGIScriptAlias`：指向上面创建的 `.wsgi` 文件。
        *   正确配置 `Directory` 区块的权限。

#### 步骤 3：配置系统策略与防火墙
*   **SELinux**：允许 Apache 进行网络连接。
    ```bash
    sudo setsebool -P httpd_can_network_connect 1
    ```
*   **防火墙**：开放 9000 端口。
    ```bash
    sudo firewall-cmd --permanent --add-port=9000/tcp
    sudo firewall-cmd --reload
    ```

### 四、 数据库配置与初始化

这是部署过程中问题最集中的环节。

#### 阶段 1：解决连接权限问题
应用启动后，出现 `Access denied for user ‘labor_app_user‘@‘::1‘` 错误。
*   **问题根源**：MySQL/MariaDB 将 `localhost` (通常指 IPv4 回环地址 `127.0.0.1` 或 Unix Socket) 与 IPv6 地址 `::1` 视为不同的主机。
*   **解决方案**：为数据库用户添加从 IPv6 地址 (`::1`) 连接的权限。
    ```sql
    -- 在 MariaDB 中执行
    CREATE USER 'labor_app_user'@'::1' IDENTIFIED BY '你的密码';
    GRANT ALL PRIVILEGES ON labor_application_db.* TO 'labor_app_user'@'::1';
    FLUSH PRIVILEGES;
    ```
*   **更优实践**：在应用配置文件 `config.py` 中，将数据库连接 URI 明确指定为 IPv4 地址，一劳永逸地避免此问题。
    ```python
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://labor_app_user:密码@127.0.0.1/labor_application_db'
    ```

#### 阶段 2：初始化生产数据库表
解决连接问题后，出现 `Table ‘labor_application_db.users‘ doesn‘t exist` 错误。
*   **问题根源**：Flask-SQLAlchemy 的 `db.create_all()` 在开发环境中运行，不会自动在生产环境的数据库中创建表。
*   **核心解决方案**：创建一个 Python 初始化脚本，并在与 **Apache 运行时完全相同的上下文** 中执行它。
    ```bash
    # 1. 编写初始化脚本 init_tables.py (内容见下方)
    # 2. 以 apache 用户身份，使用生产环境虚拟环境执行
    sudo -u apache /var/www/html/labormanagement/venv/bin/python /var/www/html/labormanagement/init_tables.py
    ```
*   **初始化脚本关键点 (`init_tables.py`)**：
    *   必须导入 `create_app` 以加载生产配置。
    *   必须在 `app.app_context()` 内调用 `db.create_all()`。
    *   可以包含创建默认用户（如 `admin` / `admin123`）和示例工作项数据的逻辑。

### 五、 上线验证与维护

#### 验证部署成功
1.  **检查服务状态**：
    ```bash
    sudo ss -tlnp | grep :9000  # 确认端口监听
    sudo systemctl status httpd # 确认Apache状态
    ```
2.  **测试应用响应**：
    ```bash
    curl -I http://192.168.31.75:9000/login
    ```
    *   **返回 `200 OK`**：部署成功。
    *   **返回 `302 Found` 并重定向至 `/login`**：同样是成功标志，表明应用中间件（如登录验证）工作正常。
3.  **最终测试**：在浏览器中访问 `http://<服务器IP>:9000` 并尝试登录。

#### 日常维护命令
| 用途 | 命令 |
| :--- | :--- |
| 重启应用 | `sudo systemctl restart httpd` |
| 查看实时错误日志 | `sudo tail -f /var/log/httpd/labormanagement_error.log` |
| 查看访问日志 | `sudo tail -f /var/log/httpd/labormanagement_access.log` |

### 六、 常见问题排查 (FAQ)

| 现象 | 可能原因 | 解决思路 |
| :--- | :--- | :--- |
| **`IndentationError` in WSGI file** | `.wsgi` 文件存在缩进或语法错误。 | 使用 `cat -A` 检查隐藏字符，或用提供的模板彻底重写该文件。 |
| **`ModuleNotFoundError`** | 虚拟环境中缺少依赖包，或 Apache 未使用虚拟环境路径。 | 确认 `pip` 包已安装，并在 Apache 配置中通过 `python-home` 正确指向虚拟环境目录。 |
| **数据库连接被拒绝** | 1. 用户密码错误。<br>2. 用户主机权限不足（如缺少 `@‘::1‘`）。<br>3. MariaDB 服务未启动。 | 1. 检查密码。<br>2. 在 MariaDB 中检查并修正用户权限。<br>3. 执行 `sudo systemctl status mariadb`。 |
| **`Table ... doesn‘t exist`** | 生产环境的数据库表未初始化。 | **严格按照手册第四部分，使用 `sudo -u apache ...` 执行初始化脚本**。 |
| **静态文件 404** | Apache 未正确配置静态文件别名或权限。 | 检查 Apache 配置中 `Alias /static` 指令及对应的 `Directory` 权限。 |

### 七、 总结
本次部署成功的关键在于：
1.  **架构选型**：采用了与现有环境兼容的、更简单的 `mod_wsgi`。
2.  **环境隔离**：深刻理解并严格区分了开发与生产环境，确保数据库初始化等操作在生产上下文执行。
3.  **权限管理**：妥善处理了系统层（SELinux、防火墙）、服务层（Apache用户）、数据层（MariaDB用户主机权限）的各级权限。
4.  **日志排查**：始终通过查看 Apache 错误日志 (`/var/log/httpd/labormanagement_error.log`) 来定位问题的精确根源。

---

这份手册整合了您部署过程中遇到的所有核心挑战与解决方案，可以作为未来维护或部署类似项目的重要参考。
