#!/bin/bash
# run.sh - 开发环境启动脚本

echo "======================================"
echo "  劳动用工管理系统 - 开发服务器"
echo "======================================"

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 检查虚拟环境
if [ -d ".venv" ]; then
    echo "✅ 使用虚拟环境：.venv"
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "✅ 使用虚拟环境：venv"
    source venv/bin/activate
else
    echo "❌ 未找到虚拟环境，请先创建："
    echo "   python3 -m venv venv"
    exit 1
fi

# 检查依赖
echo "检查依赖..."
python -c "import flask" 2>/dev/null || {
    echo "正在安装依赖..."
    pip install -r requirements.txt
}

# 加载环境变量
if [ -f "config.env" ]; then
    echo "✅ 加载环境配置：config.env"
    export $(grep -v '^#' config.env | xargs)
fi

# 检查数据库配置
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  警告：未设置 DATABASE_URL，使用默认配置"
fi

# 启动服务
echo ""
echo "启动开发服务器..."
echo "访问地址：http://127.0.0.1:5000"
echo ""

python manage.py runserver --debug
