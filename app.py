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

    # 获取基础目录
    basedir = os.path.abspath(os.path.dirname(__file__))

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
    # 用户端路由（服务端渲染）
    # =====================================================

    @app.route('/user')
    @login_required
    def user_index():
        """用户主页"""
        return render_template('user/index.html')

    @app.route('/user/apply', methods=['GET', 'POST'])
    @login_required
    def user_apply():
        """用工申请页面"""
        return render_template('user/apply.html')

    @app.route('/user/history')
    @login_required
    def user_apply_history():
        """申请历史页面"""
        return render_template('user/history.html')

    @app.route('/change-password', methods=['GET', 'POST'])
    @login_required
    def change_password():
        """修改密码页面"""
        if request.method == 'POST':
            old_password = request.form.get('old_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if not current_user.check_password(old_password):
                flash('原密码错误', 'danger')
            elif new_password != confirm_password:
                flash('两次输入的新密码不一致', 'danger')
            elif len(new_password) < 6:
                flash('新密码长度不能少于 6 位', 'danger')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('密码修改成功', 'success')
                return redirect(url_for('user_index'))

        return render_template('change_password.html')

    # =====================================================
    # 管理端路由（服务端渲染）
    # =====================================================

    @app.route('/admin/dashboard')
    @login_required
    def admin_dashboard():
        """管理员工作台"""
        if not current_user.is_admin:
            flash('需要管理员权限', 'danger')
            return redirect(url_for('user_index'))
        return render_template('admin/dashboard.html')

    @app.route('/admin/items')
    @login_required
    def admin_items():
        """分部分项管理页面"""
        if not current_user.is_admin:
            flash('需要管理员权限', 'danger')
            return redirect(url_for('user_index'))
        return render_template('admin/items.html')

    @app.route('/admin/import')
    @login_required
    def admin_import():
        """Excel 导入页面"""
        if not current_user.is_admin:
            flash('需要管理员权限', 'danger')
            return redirect(url_for('user_index'))
        return render_template('admin/import.html')

    @app.route('/admin/reports')
    @login_required
    def admin_reports():
        """报表统计页面"""
        if not current_user.is_admin:
            flash('需要管理员权限', 'danger')
            return redirect(url_for('user_index'))
        return render_template('admin/reports.html')

    @app.route('/admin/users')
    @login_required
    def admin_users():
        """用户管理页面"""
        if not current_user.is_admin:
            flash('需要管理员权限', 'danger')
            return redirect(url_for('user_index'))
        return render_template('admin/users.html')

    # =====================================================
    # 用户申请相关路由
    # =====================================================

    @app.route('/user/apply/submit', methods=['POST'])
    @login_required
    def user_apply_submit():
        """提交用工申请"""
        from models import ApplicationItem
        try:
            # 获取表单数据
            work_items = request.form.getlist('workItems')
            apply_date = request.form.get('apply_date')
            apply_reason = request.form.get('apply_reason', '')

            if not work_items:
                flash('请至少选择一个工作项', 'danger')
                return redirect(url_for('user_apply'))

            # 创建申请
            application = LaborApplication(
                user_id=current_user.id,
                apply_date=datetime.strptime(apply_date, '%Y-%m-%d').date() if apply_date else datetime.now().date(),
                reason=apply_reason,
                status='pending'
            )
            db.session.add(application)
            db.session.flush()  # 获取 application id

            # 添加申请项目
            for item_data in work_items:
                if item_data:
                    import json
                    item = json.loads(item_data)
                    app_item = ApplicationItem(
                        application_id=application.id,
                        work_item_id=item.get('work_item_id'),
                        quantity=float(item.get('quantity', 0)),
                        work_content=item.get('work_content', '')
                    )
                    db.session.add(app_item)

            db.session.commit()
            flash('申请提交成功', 'success')
            return redirect(url_for('user_apply_history'))

        except Exception as e:
            db.session.rollback()
            app.logger.error(f'提交申请失败：{e}')
            flash('提交申请失败：' + str(e), 'danger')
            return redirect(url_for('user_apply'))

    @app.route('/export/pdf/<int:application_id>')
    @login_required
    def export_pdf(application_id):
        """导出申请单为 PDF"""
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from io import BytesIO
        import os

        # 获取申请详情
        application = LaborApplication.query.get_or_404(application_id)

        # 权限检查：只能导出自己的申请，管理员可以导出所有
        if not current_user.is_admin and application.user_id != current_user.id:
            flash('无权访问', 'danger')
            return redirect(url_for('user_apply_history'))

        try:
            # 创建 PDF
            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4

            # 注册中文字体（如果存在）
            font_path = os.path.join(os.path.dirname(__file__), 'static', 'fonts', 'SimHei.ttf')
            if os.path.exists(font_path):
                pdfmetrics.RegisterFont(TTFont('SimHei', font_path))
                font_name = 'SimHei'
            else:
                font_name = 'Helvetica'

            # 标题
            p.setFont(font_name, 18)
            p.drawCentredString(width / 2, height - 50, '用工申请单')

            # 申请信息
            p.setFont(font_name, 12)
            y = height - 100
            p.drawString(50, y, f'申请编号：{application.id}')
            y -= 25
            p.drawString(50, y, f'申请人：{application.user.display_name if application.user else "Unknown"}')
            y -= 25
            p.drawString(50, y, f'申请日期：{application.apply_date}')
            y -= 25
            p.drawString(50, y, f'状态：{application.status}')
            y -= 25
            p.drawString(50, y, f'申请理由：{application.reason or "无"}')

            # 工作项列表
            y -= 40
            p.drawString(50, y, '工作项明细：')
            y -= 25
            for i, item in enumerate(application.application_items):
                p.drawString(50, y, f'{i+1}. {item.work_item.name if item.work_item else "Unknown"} - 数量：{item.quantity}')
                y -= 20

            p.save()

            # 发送文件
            buffer.seek(0)
            return send_file(
                buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'application_{application.id}.pdf'
            )
        except Exception as e:
            app.logger.error(f'导出 PDF 失败：{e}')
            flash('导出 PDF 失败：' + str(e), 'danger')
            return redirect(url_for('user_apply_history'))

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

    # 全局参考系数（默认 1.0）
    reference_coefficient = 1.0

    # 尝试从文件加载参考系数
    config_file = os.path.join(basedir, 'config.json')
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                reference_coefficient = config_data.get('reference_coefficient', 1.0)
        except:
            pass

    @app.context_processor
    def inject_globals():
        """注入全局变量到模板"""
        return {
            'app_name': '劳动用工管理系统',
            'version': '2.0.0',
            'current_reference_coefficient': reference_coefficient
        }

    # =====================================================
    # 参考系数管理
    # =====================================================

    @app.route('/admin/update-reference-coefficient', methods=['POST'])
    @login_required
    def update_reference_coefficient():
        """更新参考系数（仅管理员）"""
        from flask import request as req
        if not current_user.is_admin:
            return error_response('需要管理员权限', 403)

        data = req.get_json()
        coefficient = data.get('coefficient')

        if coefficient is None:
            return error_response('缺少系数参数', 400)

        try:
            coefficient = float(coefficient)
            if coefficient < 0.7 or coefficient > 1.0:
                return error_response('参考系数必须在 0.7-1.0 之间', 400)

            nonlocal reference_coefficient
            reference_coefficient = coefficient

            # 保存到文件
            config_file = os.path.join(basedir, 'config.json')
            config_data = {'reference_coefficient': coefficient}
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)

            return success_response({'coefficient': coefficient}, message='参考系数已更新')
        except ValueError:
            return error_response('系数必须是数字', 400)

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
