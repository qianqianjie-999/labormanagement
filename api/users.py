"""
用户管理 API
"""
from flask import Blueprint, request
from flask_login import login_required, current_user
from sqlalchemy import or_

from models import db, User
from .utils import (
    success_response, error_response, validate_json,
    paginate_response, admin_required_api
)

users_bp = Blueprint('api_users', __name__, url_prefix='/api/users')


@users_bp.route('', methods=['GET'])
@login_required
def get_users():
    """获取用户列表（分页）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    keyword = request.args.get('keyword', '')
    department = request.args.get('department', '')

    query = User.query

    if keyword:
        query = query.filter(
            or_(
                User.username.contains(keyword),
                User.display_name.contains(keyword),
                User.email.contains(keyword)
            )
        )

    if department:
        query = query.filter(User.department == department)

    # 普通用户只能查看自己和管理员
    if not current_user.is_admin:
        query = query.filter(
            or_(
                User.id == current_user.id,
                User.is_admin == True
            )
        )

    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    users = [user.to_dict() for user in pagination.items]

    return paginate_response(
        items=users,
        total=pagination.total,
        page=page,
        per_page=per_page,
        has_next=pagination.has_next,
        has_prev=pagination.has_prev
    )


@users_bp.route('/<int:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    """获取单个用户详情"""
    user = User.query.get_or_404(user_id)

    # 权限检查
    if not current_user.is_admin and user.id != current_user.id:
        return error_response('无权查看', 403)

    return success_response({'user': user.to_dict()})


@users_bp.route('', methods=['POST'])
@admin_required_api
@validate_json('username', 'display_name', 'password')
def create_user():
    """创建新用户（仅管理员）"""
    data = request.get_json()

    # 检查用户名是否已存在
    if User.query.filter_by(username=data['username']).first():
        return error_response('用户名已存在', 400)

    user = User(
        username=data['username'],
        display_name=data['display_name'],
        password=data['password'],
        email=data.get('email'),
        department=data.get('department'),
        is_admin=data.get('is_admin', False)
    )

    db.session.add(user)
    db.session.commit()

    return success_response({'user': user.to_dict()}, message='用户创建成功', code=201)


@users_bp.route('/<int:user_id>', methods=['PUT'])
@admin_required_api
@validate_json('display_name')
def update_user(user_id):
    """更新用户信息（仅管理员）"""
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    user.display_name = data['display_name']

    if 'email' in data:
        user.email = data['email']
    if 'department' in data:
        user.department = data['department']
    if 'is_admin' in data:
        user.is_admin = data['is_admin']
    if 'is_active' in data:
        user.is_active = data['is_active']

    db.session.commit()

    return success_response({'user': user.to_dict()}, message='用户更新成功')


@users_bp.route('/<int:user_id>', methods=['DELETE'])
@admin_required_api
def delete_user(user_id):
    """删除用户（仅管理员）"""
    user = User.query.get_or_404(user_id)

    # 不能删除自己
    if user.id == current_user.id:
        return error_response('不能删除自己的账户', 400)

    db.session.delete(user)
    db.session.commit()

    return success_response(message='用户删除成功')


@users_bp.route('/departments', methods=['GET'])
@login_required
def get_departments():
    """获取所有部门列表"""
    departments = db.session.query(User.department).filter(
        User.department.isnot(None)
    ).distinct().all()

    return success_response({
        'departments': [d[0] for d in departments if d[0]]
    })
