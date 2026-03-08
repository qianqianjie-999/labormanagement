"""
API 响应工具函数
"""
from functools import wraps
from flask import jsonify, request, current_app
from flask_login import current_user


def success_response(data=None, message='success', code=200):
    """成功响应"""
    return jsonify({
        'code': code,
        'message': message,
        'data': data
    }), code


def error_response(message='error', code=400, errors=None):
    """错误响应"""
    response = {
        'code': code,
        'message': message
    }
    if errors:
        response['errors'] = errors
    return jsonify(response), code


def paginate_response(items, total, page, per_page, has_next, has_prev):
    """分页响应"""
    return success_response({
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'has_next': has_next,
        'has_prev': has_prev,
        'pages': (total + per_page - 1) // per_page
    })


def login_required_api(f):
    """API 登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return error_response('请先登录', 401)
        return f(*args, **kwargs)
    return decorated_function


def admin_required_api(f):
    """管理员权限验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return error_response('请先登录', 401)
        if not current_user.is_admin:
            return error_response('需要管理员权限', 403)
        return f(*args, **kwargs)
    return decorated_function


def validate_json(*required_fields):
    """验证 JSON 请求数据装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return error_response('Content-Type 应为 application/json', 400)

            data = request.get_json()
            missing_fields = [field for field in required_fields if field not in data]

            if missing_fields:
                return error_response(
                    f'缺少必需字段：{", ".join(missing_fields)}',
                    400
                )

            return f(*args, **kwargs)
        return decorated_function
    return decorator
