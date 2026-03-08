"""
认证相关 API
"""
from flask import Blueprint, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timezone

from models import db, User
from .utils import success_response, error_response, validate_json

auth_bp = Blueprint('api_auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/login', methods=['POST'])
@validate_json('username', 'password')
def login():
    """
    用户登录
    ---
    tags:
      - 认证
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            username:
              type: string
            password:
              type: string
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if not user:
        return error_response('用户名或密码错误', 401)

    if not user.check_password(password):
        return error_response('用户名或密码错误', 401)

    if not user.is_active:
        return error_response('账户已被禁用', 403)

    # 更新最后登录时间
    user.last_login = datetime.now(timezone.utc)
    db.session.commit()

    login_user(user, remember=data.get('remember', False))

    return success_response({
        'user': user.to_dict(),
        'token': user.id  # 简化版，生产环境应使用 JWT
    })


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """用户登出"""
    logout_user()
    return success_response(message='已退出登录')


@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """获取当前登录用户信息"""
    return success_response({'user': current_user.to_dict()})


@auth_bp.route('/change-password', methods=['POST'])
@login_required
@validate_json('old_password', 'new_password')
def change_password():
    """修改密码"""
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')

    if not current_user.check_password(old_password):
        return error_response('原密码错误', 400)

    if len(new_password) < 6:
        return error_response('新密码长度至少为 6 位', 400)

    current_user.set_password(new_password)
    db.session.commit()

    return success_response(message='密码修改成功')
