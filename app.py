# app.py - 用工申请管理系统主程序（前后端分离版本）
"""
劳动用工管理系统 - 后端 API 服务

支持两种模式：
1. API 模式：前后端分离，提供 RESTful API
2. 混合模式：同时支持 API 和传统服务端渲染（向后兼容）

运行方式：
    python app.py                    # 开发模式
    python manage.py runserver       # 使用管理脚本
    gunicorn app:app -w 4 -b 0.0.0.0:5000  # 生产模式
"""

import json
import os
from datetime import datetime, timedelta, timezone
from io import BytesIO
from functools import wraps

import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入配置和模型
from config import config
from models import db, User, WorkItem, ApplicationItem, LaborApplication
from logging_config import setup_logging

# 导入 API 蓝图
from api.auth import auth_bp
from api.users import users_bp
from api.work_items import work_items_bp
from api.applications import applications_bp
from api.utils import success_response, error_response

# =====================================================
# 创建 Flask 应用
# =====================================================

def create_app(config_name=None):
    """
    应用工厂函数

    Args:
        config_name: 配置名称 (development, production, testing)

    Returns:
        Flask 应用实例
    """
    app = Flask(__name__, static_folder='static', static_url_path='/static')

    # 加载配置
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config.get(config_name, config['development']))

    # 应用额外配置
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', app.config['SECRET_KEY'])
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', app.config['SQLALCHEMY_DATABASE_URI'])
    app.config['LOG_LEVEL'] = os.getenv('LOG_LEVEL', app.config['LOG_LEVEL'])

    # 配置跨域（CORS）
    cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173')
    CORS(app,
         origins=cors_origins.split(','),
         supports_credentials=os.getenv('CORS_SUPPORTS_CREDENTIALS', 'true').lower() == 'true',
         methods=os.getenv('CORS_METHODS', 'GET,POST,PUT,DELETE,OPTIONS').split(','),
         allow_headers=os.getenv('CORS_ALLOW_HEADERS', 'Content-Type,Authorization').split(','))

    # 确保目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PDF_EXPORT_FOLDER'], exist_ok=True)
    os.makedirs(app.config['LOG_FOLDER'], exist_ok=True)

    # 初始化数据库
    db.init_app(app)

    # 初始化 Flask-Login（仅用于会话管理）
    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # 配置登录视图
    login_manager.login_view = 'login'
    login_manager.login_message_category = 'warning'

    # 自定义未授权响应（API 模式）
    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith('/api/'):
            return error_response('请先登录', 401)
        return redirect(url_for('login', next=request.url))

    # 初始化日志
    setup_logging(app)

    # =====================================================
    # 注册蓝图
    # =====================================================

    # API 路由
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(work_items_bp)
    app.register_blueprint(applications_bp)

    # =====================================================
    # 辅助函数
    # =====================================================

    def allowed_file(filename):
        """检查文件扩展名是否允许"""
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

    # =====================================================
    # 传统服务端渲染路由（向后兼容）
    # =====================================================

    @app.route('/')
    @login_required
    def index():
        """首页（传统模式）"""
        return redirect(url_for('dashboard'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        """工作台（传统模式）"""
        return render_template('admin/dashboard.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """登录页面（传统模式）"""
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            remember = request.form.get('remember', False)

            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password) and user.is_active:
                login_user(user, remember=remember)
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('index'))
            flash('用户名或密码错误', 'danger')

        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        """登出（传统模式）"""
        logout_user()
        return redirect(url_for('login'))

    # =====================================================
    # 静态文件服务（开发模式）
    # =====================================================

    @app.route('/static/<path:filename>')
    def serve_static(filename):
        """服务静态文件"""
        return send_from_directory(app.static_folder, filename)

    # =====================================================
    # 健康检查
    # =====================================================

    @app.route('/api/health', methods=['GET'])
    def health_check():
        """健康检查接口"""
        return success_response({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '2.0.0'
        })

    # =====================================================
    # 错误处理
    # =====================================================

    @app.errorhandler(404)
    def not_found(error):
        return error_response('资源不存在', 404)

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f'内部错误：{error}')
        return error_response('服务器内部错误', 500)

    @app.errorhandler(400)
    def bad_request(error):
        return error_response('请求参数错误', 400)

    # =====================================================
    # 应用上下文处理器
    # =====================================================

    @app.context_processor
    def inject_globals():
        """注入全局变量到模板"""
        return {
            'app_name': '劳动用工管理系统',
            'version': '2.0.0'
        }

    app.logger.info(f"应用初始化完成 - 环境：{config_name}")
    return app


# =====================================================
# 主程序入口
# =====================================================

# 创建应用实例
app = create_app()

if __name__ == '__main__':
    # 开发服务器
    host = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_RUN_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

    print("=" * 50)
    print("  劳动用工管理系统 - 开发服务器")
    print("=" * 50)
    print(f"  访问地址：http://{host}:{port}")
    print(f"  API 文档：http://{host}:{port}/api/health")
    print(f"  调试模式：{debug}")
    print("=" * 50)

    app.run(host=host, port=port, debug=debug)
