#!/bin/bash
# =====================================================
# 数据库初始化脚本
# 用法：./scripts/init_db.sh [mysql_host] [mysql_user]
# =====================================================

set -e

# 配置
MYSQL_HOST=${1:-"127.0.0.1"}
MYSQL_USER=${2:-"root"}
DB_NAME="labor_application_db"
DB_USER="labor_app_user"
DB_PASS="labor_app_password"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "======================================"
echo "  劳动用工管理系统 - 数据库初始化"
echo "======================================"
echo ""
echo "MySQL 主机：$MYSQL_HOST"
echo "MySQL 用户：$MYSQL_USER"
echo "目标数据库：$DB_NAME"
echo ""

# 读取密码
read -sp "请输入 MySQL root 密码：" MYSQL_PASS
echo ""

# 执行初始化脚本
echo "正在执行初始化脚本..."
mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASS" < "$PROJECT_DIR/database/init.sql"

echo ""
echo "======================================"
echo "  ✅ 数据库初始化完成！"
echo "======================================"
echo ""
echo "数据库信息："
echo "  数据库名：$DB_NAME"
echo "  用户名：$DB_USER"
echo "  密码：$DB_PASS"
echo "  主机：$MYSQL_HOST"
echo ""
echo "默认账户："
echo "  管理员：admin / admin123"
echo "  普通用户：user1 / user123"
echo ""
echo "⚠️  请首次登录后立即修改默认密码！"
echo ""
