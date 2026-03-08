"""
工作项管理 API
"""
from flask import Blueprint, request
from flask_login import login_required, current_user
from sqlalchemy import func

from models import db, WorkItem
from .utils import (
    success_response, error_response, validate_json,
    paginate_response, admin_required_api
)

work_items_bp = Blueprint('api_work_items', __name__, url_prefix='/api/work-items')


@work_items_bp.route('', methods=['GET'])
@login_required
def get_work_items():
    """获取工作项列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category = request.args.get('category', '')
    keyword = request.args.get('keyword', '')

    query = WorkItem.query

    if category:
        query = query.filter(WorkItem.category == category)
    if keyword:
        query = query.filter(
            func.lower(WorkItem.name).contains(func.lower(keyword))
        )

    pagination = query.order_by(WorkItem.code).paginate(
        page=page, per_page=per_page, error_out=False
    )

    hide_coefficient = not current_user.is_admin
    items = [item.to_dict(hide_coefficient) for item in pagination.items]

    return paginate_response(
        items=items,
        total=pagination.total,
        page=page,
        per_page=per_page,
        has_next=pagination.has_next,
        has_prev=pagination.has_prev
    )


@work_items_bp.route('/categories', methods=['GET'])
@login_required
def get_categories():
    """获取所有分类列表"""
    categories = db.session.query(WorkItem.category).distinct().all()
    return success_response({
        'categories': [c[0] for c in categories if c[0]]
    })


@work_items_bp.route('/<int:item_id>', methods=['GET'])
@login_required
def get_work_item(item_id):
    """获取单个工作项详情"""
    item = WorkItem.query.get_or_404(item_id)
    hide_coefficient = not current_user.is_admin
    return success_response({'item': item.to_dict(hide_coefficient)})


@work_items_bp.route('', methods=['POST'], endpoint='api_add_item')
@admin_required_api
@validate_json('code', 'name', 'labor_coefficient', 'unit', 'category')
def create_work_item():
    """创建工作项（仅管理员）"""
    data = request.get_json()

    # 检查代码是否已存在
    if WorkItem.query.filter_by(code=data['code']).first():
        return error_response('工作项代码已存在', 400)

    item = WorkItem(
        code=data['code'],
        name=data['name'],
        labor_coefficient=float(data['labor_coefficient']),
        unit=data['unit'],
        category=data['category']
    )

    db.session.add(item)
    db.session.commit()

    return success_response({'item': item.to_dict()}, message='工作项创建成功', code=201)


# 为模板 url_for 添加别名endpoint
work_items_bp.add_url_rule('/create', 'api_add_item', create_work_item, methods=['POST'])


@work_items_bp.route('/<int:item_id>', methods=['PUT'], endpoint='api_update_item')
@admin_required_api
@validate_json('name', 'labor_coefficient', 'unit', 'category')
def update_work_item(item_id):
    """更新工作项（仅管理员）"""
    item = WorkItem.query.get_or_404(item_id)
    data = request.get_json()

    item.name = data['name']
    item.labor_coefficient = float(data['labor_coefficient'])
    item.unit = data['unit']
    item.category = data['category']

    db.session.commit()

    return success_response({'item': item.to_dict()}, message='工作项更新成功')


@work_items_bp.route('/<int:item_id>', methods=['DELETE'], endpoint='api_delete_item')
@admin_required_api
def delete_work_item(item_id):
    """删除工作项（仅管理员）"""
    item = WorkItem.query.get_or_404(item_id)

    # 检查是否被申请引用
    from models import ApplicationItem
    if ApplicationItem.query.filter_by(work_item_id=item_id).first():
        return error_response('该工作项已被使用，无法删除', 400)

    db.session.delete(item)
    db.session.commit()

    return success_response(message='工作项删除成功')


@work_items_bp.route('/import', methods=['POST'])
@admin_required_api
def import_work_items():
    """批量导入工作项（从 Excel）"""
    from io import BytesIO
    import pandas as pd
    from werkzeug.utils import secure_filename

    if 'file' not in request.files:
        return error_response('未找到上传文件', 400)

    file = request.files['file']
    if file.filename == '':
        return error_response('未选择文件', 400)

    allowed_extensions = {'xlsx', 'xls'}
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''

    if ext not in allowed_extensions:
        return error_response('仅支持 Excel 文件（.xlsx, .xls）', 400)

    try:
        # 读取 Excel 文件
        df = pd.read_excel(BytesIO(file.read()))

        # 验证必需列
        required_columns = ['code', 'name', 'labor_coefficient', 'unit', 'category']
        missing = [c for c in required_columns if c not in df.columns]
        if missing:
            return error_response(f'缺少必需列：{", ".join(missing)}', 400)

        success_count = 0
        error_items = []

        for index, row in df.iterrows():
            try:
                # 检查代码是否已存在
                if WorkItem.query.filter_by(code=str(row['code'])).first():
                    error_items.append(f"行{index + 2}: 代码 {row['code']} 已存在")
                    continue

                item = WorkItem(
                    code=str(row['code']),
                    name=str(row['name']),
                    labor_coefficient=float(row['labor_coefficient']),
                    unit=str(row['unit']),
                    category=str(row['category'])
                )
                db.session.add(item)
                success_count += 1
            except Exception as e:
                error_items.append(f"行{index + 2}: {str(e)}")

        db.session.commit()

        result = {'success_count': success_count}
        if error_items:
            result['errors'] = error_items

        return success_response(result, message=f'成功导入 {success_count} 条记录')

    except Exception as e:
        return error_response(f'导入失败：{str(e)}', 500)
