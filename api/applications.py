"""
用工申请 API
"""
from flask import Blueprint, request
from flask_login import login_required, current_user
from datetime import datetime, timezone
from sqlalchemy import or_, desc

from models import db, LaborApplication, ApplicationItem, WorkItem
from .utils import (
    success_response, error_response, validate_json,
    paginate_response, login_required_api
)

applications_bp = Blueprint('api_applications', __name__, url_prefix='/api/applications')


@applications_bp.route('', methods=['GET'])
@login_required
def get_applications():
    """获取申请列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    status = request.args.get('status', '')
    department = request.args.get('department', '')

    query = LaborApplication.query

    # 管理员可以看到所有申请，普通用户只能看到自己的
    if not current_user.is_admin:
        query = query.filter(LaborApplication.user_id == current_user.id)

    if status:
        query = query.filter(LaborApplication.status == status)
    if department:
        query = query.filter(LaborApplication.department == department)

    pagination = query.order_by(desc(LaborApplication.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )

    hide_coefficient = not current_user.is_admin
    items = [app.to_dict(hide_coefficient) for app in pagination.items]

    return paginate_response(
        items=items,
        total=pagination.total,
        page=page,
        per_page=per_page,
        has_next=pagination.has_next,
        has_prev=pagination.has_prev
    )


@applications_bp.route('/<int:app_id>', methods=['GET'])
@login_required
def get_application(app_id):
    """获取申请详情"""
    app = LaborApplication.query.get_or_404(app_id)

    # 权限检查
    if not current_user.is_admin and app.user_id != current_user.id:
        return error_response('无权查看', 403)

    hide_coefficient = not current_user.is_admin
    return success_response({'application': app.to_dict(hide_coefficient)})


@applications_bp.route('', methods=['POST'])
@login_required
@validate_json('department', 'applicant', 'project_name', 'items')
def create_application():
    """创建新的用工申请"""
    data = request.get_json()

    application = LaborApplication(
        department=data['department'],
        applicant=data['applicant'],
        project_name=data['project_name'],
        project_description=data.get('project_description', ''),
        worker_names=data.get('worker_names', ''),
        user_id=current_user.id
    )

    # 处理申请明细
    total_required = 0
    total_user_proposed = 0

    for item_data in data.get('items', []):
        work_item = WorkItem.query.get(item_data.get('work_item_id'))
        if not work_item:
            return error_response(f"工作项不存在：{item_data.get('work_item_id')}", 400)

        quantity = float(item_data.get('quantity', 0))
        user_proposed = item_data.get('user_proposed_labor')

        app_item = ApplicationItem(
            work_item_id=work_item.id,
            quantity=quantity,
            work_item=work_item,
            user_proposed_labor=user_proposed
        )

        application.items.append(app_item)
        total_required += app_item.required_labor
        if user_proposed:
            total_user_proposed += float(user_proposed)

    application.total_required_labor = total_required
    application.total_user_proposed = total_user_proposed

    db.session.add(application)
    db.session.commit()

    return success_response(
        {'application': application.to_dict()},
        message='申请提交成功',
        code=201
    )


@applications_bp.route('/<int:app_id>', methods=['PUT'])
@login_required
def update_application(app_id):
    """更新申请（仅限待处理状态且为申请人）"""
    app = LaborApplication.query.get_or_404(app_id)

    # 权限检查
    if not current_user.is_admin and app.user_id != current_user.id:
        return error_response('无权修改', 403)

    # 状态检查
    if app.status != 'pending':
        return error_response('已审批的申请无法修改', 400)

    data = request.get_json()

    if 'department' in data:
        app.department = data['department']
    if 'applicant' in data:
        app.applicant = data['applicant']
    if 'project_name' in data:
        app.project_name = data['project_name']
    if 'project_description' in data:
        app.project_description = data['project_description']
    if 'worker_names' in data:
        app.worker_names = data['worker_names']

    db.session.commit()

    return success_response(
        {'application': app.to_dict()},
        message='申请更新成功'
    )


@applications_bp.route('/<int:app_id>', methods=['DELETE'])
@login_required
def delete_application(app_id):
    """删除申请（仅限待处理状态）"""
    app = LaborApplication.query.get_or_404(app_id)

    # 权限检查
    if not current_user.is_admin and app.user_id != current_user.id:
        return error_response('无权删除', 403)

    # 状态检查
    if app.status != 'pending':
        return error_response('已审批的申请无法删除', 400)

    db.session.delete(app)
    db.session.commit()

    return success_response(message='申请删除成功')


@applications_bp.route('/<int:app_id>/approve', methods=['POST'])
@admin_required_api
@validate_json('status', 'approved_labor')
def approve_application(app_id):
    """审批申请"""
    app = LaborApplication.query.get_or_404(app_id)

    if app.status != 'pending':
        return error_response('该申请已审批', 400)

    data = request.get_json()

    app.status = data['status']  # 'approved' or 'rejected'
    app.approved_by = current_user.display_name
    app.approval_comment = data.get('approval_comment', '')
    app.approved_labor = float(data['approved_labor'])
    app.approval_time = datetime.now(timezone.utc)

    db.session.commit()

    status_msg = '审批通过' if data['status'] == 'approved' else '申请已驳回'
    return success_response(
        {'application': app.to_dict()},
        message=status_msg
    )


@applications_bp.route('/stats', methods=['GET'])
@login_required
def get_statistics():
    """获取统计数据"""
    query = LaborApplication.query

    if not current_user.is_admin:
        query = query.filter(LaborApplication.user_id == current_user.id)

    stats = {
        'total': query.count(),
        'pending': query.filter_by(status='pending').count(),
        'approved': query.filter_by(status='approved').count(),
        'rejected': query.filter_by(status='rejected').count()
    }

    # 计算用工总量
    from sqlalchemy import func
    if current_user.is_admin:
        total_labor = db.session.query(func.sum(LaborApplication.total_required_labor)).filter(
            LaborApplication.status == 'approved'
        ).scalar() or 0
        approved_labor = db.session.query(func.sum(LaborApplication.approved_labor)).filter(
            LaborApplication.status == 'approved'
        ).scalar() or 0
    else:
        total_labor = db.session.query(func.sum(LaborApplication.total_required_labor)).filter(
            LaborApplication.user_id == current_user.id,
            LaborApplication.status == 'approved'
        ).scalar() or 0
        approved_labor = db.session.query(func.sum(LaborApplication.approved_labor)).filter(
            LaborApplication.user_id == current_user.id,
            LaborApplication.status == 'approved'
        ).scalar() or 0

    stats['total_required_labor'] = float(total_labor)
    stats['total_approved_labor'] = float(approved_labor)

    return success_response({'stats': stats})
