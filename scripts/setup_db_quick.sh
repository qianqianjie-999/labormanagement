#!/bin/bash
# =====================================================
# 快速数据库初始化脚本
# 用法：./setup_db_quick.sh
# =====================================================

echo "======================================"
echo "  劳动用工管理系统 - 数据库快速设置"
echo "======================================"

# 检查 MySQL 是否运行
if ! pgrep -x "mysqld" > /dev/null 2>&1; then
    echo "⚠️  MySQL/MariaDB 服务未运行"
    echo "请先启动服务："
    echo "  sudo systemctl start mariadb"
    echo "  sudo systemctl enable mariadb"
    exit 1
fi

echo "✅ MySQL/MariaDB 服务正在运行"
echo ""

# 执行初始化
echo "正在执行数据库初始化..."
echo "需要输入 sudo 密码："
sudo mysql < database/init.sql

if [ $? -eq 0 ]; then
    echo ""
    echo "======================================"
    echo "  ✅ 数据库初始化完成！"
    echo "======================================"
    echo ""
    echo "数据库信息："
    echo "  数据库名：labor_application_db"
    echo "  用户名：labor_app_user"
    echo "  密码：labor_app_password"
    echo ""
    echo "默认账户："
    echo "  管理员：admin / admin123"
    echo "  普通用户：user1 / user123"
    echo ""
    echo "⚠️  请首次登录后立即修改默认密码！"
    echo ""
else
    echo ""
    echo "❌ 数据库初始化失败！"
    echo "请检查 MySQL 服务状态或手动执行："
    echo "  sudo mysql < database/init.sql"
    exit 1
fi
