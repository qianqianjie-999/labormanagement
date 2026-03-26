from flask_sqlalchemy import SQLAlchemy
from datetime import datetime,timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, current_user  # 添加 current_user 导入
db = SQLAlchemy()


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120))
    department = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)

    # 关系：一个用户可以创建多个用工申请
    applications = db.relationship('LaborApplication', backref='user', lazy=True,
                                   foreign_keys='LaborApplication.user_id')

    def __init__(self, username, display_name, password, **kwargs):
        self.username = username
        self.display_name = display_name
        self.set_password(password)
        for key, value in kwargs.items():
            setattr(self, key, value)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def update_last_login(self):
        self.last_login = datetime.utcnow()
        db.session.commit()

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'display_name': self.display_name,
            'email': self.email,
            'department': self.department,
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M:%S') if self.last_login else None
        }

    def __repr__(self):
        return f'<User {self.username}>'


class WorkItem(db.Model):
    __tablename__ = 'work_items'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    labor_coefficient = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'labor_coefficient': self.labor_coefficient,
            'unit': self.unit,
            'category': self.category
        }

    def __repr__(self):
        return f'<WorkItem {self.code}: {self.name}>'


class ApplicationItem(db.Model):
    """申请明细项 - 包含快照功能"""
    __tablename__ = 'application_items'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('labor_applications.id'), nullable=False)
    work_item_id = db.Column(db.Integer, db.ForeignKey('work_items.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    required_labor = db.Column(db.Float, nullable=False)
    user_proposed_labor = db.Column(db.Float, nullable=True)  # 新增：用户输入的拟申请用工

    # 快照字段 - 申请时锁定数据
    snapshot_code = db.Column(db.String(20))
    snapshot_name = db.Column(db.String(100))
    snapshot_labor_coefficient = db.Column(db.Float)
    snapshot_unit = db.Column(db.String(20))
    snapshot_category = db.Column(db.String(50))

    # 关系
    work_item = db.relationship('WorkItem')

    def __init__(self, work_item_id, quantity, work_item=None, user_proposed_labor=None):
        self.work_item_id = work_item_id
        self.quantity = quantity
        self.user_proposed_labor = user_proposed_labor

        # 如果有 work_item 对象，创建快照
        if work_item:
            self.snapshot_code = work_item.code
            self.snapshot_name = work_item.name
            self.snapshot_labor_coefficient = work_item.labor_coefficient
            self.snapshot_unit = work_item.unit
            self.snapshot_category = work_item.category
            self.required_labor = quantity * work_item.labor_coefficient
        else:
            # 如果没有传入 work_item，尝试从数据库加载
            work_item_obj = WorkItem.query.get(work_item_id)
            if work_item_obj:
                self.snapshot_code = work_item_obj.code
                self.snapshot_name = work_item_obj.name
                self.snapshot_labor_coefficient = work_item_obj.labor_coefficient
                self.snapshot_unit = work_item_obj.unit
                self.snapshot_category = work_item_obj.category
                self.required_labor = quantity * work_item_obj.labor_coefficient

    def get_work_item_data(self):
        """获取工作项数据（优先使用快照）"""
        if self.snapshot_code:
            return {
                'code': self.snapshot_code,
                'name': self.snapshot_name,
                'labor_coefficient': self.snapshot_labor_coefficient,
                'unit': self.snapshot_unit,
                'category': self.snapshot_category,
                'is_snapshot': True
            }
        elif self.work_item:
            return {
                'code': self.work_item.code,
                'name': self.work_item.name,
                'labor_coefficient': self.work_item.labor_coefficient,
                'unit': self.work_item.unit,
                'category': self.work_item.category,
                'is_snapshot': False
            }
        return None

    def to_dict(self, hide_coefficient=False):
        data = {
            'id': self.id,
            'quantity': self.quantity,
            'required_labor': self.required_labor,
            'user_proposed_labor': self.user_proposed_labor
        }

        work_item_data = self.get_work_item_data()
        if work_item_data:
            if hide_coefficient and not current_user.is_admin:
                # 普通用户隐藏系数
                work_item_data['labor_coefficient'] = '***'
            data['work_item'] = work_item_data

        return data

    def __repr__(self):
        return f'<ApplicationItem {self.id}>'


class LaborApplication(db.Model):
    __tablename__ = 'labor_applications'

    id = db.Column(db.Integer, primary_key=True)
    department = db.Column(db.String(100), nullable=False)
    applicant = db.Column(db.String(50), nullable=False)
    project_name = db.Column(db.String(200), nullable=False)
    project_description = db.Column(db.Text)
    worker_names = db.Column(db.Text)
    total_required_labor = db.Column(db.Float, default=0.0)
    total_user_proposed = db.Column(db.Float, default=0.0)  # 新增：用户申请的总人工
    status = db.Column(db.String(20), default='pending')

    # 添加审批相关字段
    approved_by = db.Column(db.String(100))  # 审批人
    approval_comment = db.Column(db.Text)  # 审批意见
    approval_time = db.Column(db.DateTime)  # 审批时间
    approved_labor = db.Column(db.Float)  # 新增：审批后的人工数

    # PDF 附件字段 - 用于存储签字扫描版 PDF
    signed_pdf_filename = db.Column(db.String(255))  # 上传的 PDF 文件名
    pdf_uploaded_at = db.Column(db.DateTime)  # PDF 上传时间
    pdf_uploaded_by = db.Column(db.String(50))  # PDF 上传人

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联用户
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # 明细项
    items = db.relationship('ApplicationItem', backref='application',
                            lazy=True, cascade='all, delete-orphan')

    def to_dict(self, hide_coefficient=False):
        from datetime import timedelta

        # UTC 时间转换为北京时间（UTC+8）
        local_created_at = self.created_at + timedelta(hours=8) if self.created_at else None
        local_approval_time = self.approval_time + timedelta(hours=8) if self.approval_time else None
        local_pdf_uploaded = self.pdf_uploaded_at + timedelta(hours=8) if self.pdf_uploaded_at else None

        return {
            'id': self.id,
            'department': self.department,
            'applicant': self.applicant,
            'project_name': self.project_name,
            'project_description': self.project_description,
            'worker_names': self.worker_names,
            'total_required_labor': float(self.total_required_labor) if self.total_required_labor else 0.0,
            'total_user_proposed': float(self.total_user_proposed) if self.total_user_proposed else 0.0,
            'approved_labor': float(self.approved_labor) if self.approved_labor else None,
            'status': self.status,
            'approved_by': self.approved_by,
            'approval_comment': self.approval_comment,
            'approval_time': self.approval_time.strftime('%Y-%m-%d %H:%M:%S') if self.approval_time else None,
            'local_approval_time': local_approval_time.strftime('%Y-%m-%d %H:%M:%S') if local_approval_time else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'local_created_at': local_created_at.strftime('%Y-%m-%d %H:%M:%S') if local_created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'user_id': self.user_id,
            'items': [item.to_dict(hide_coefficient) for item in self.items],
            # PDF 附件信息
            'signed_pdf_filename': self.signed_pdf_filename,
            'pdf_uploaded_at': local_pdf_uploaded.strftime('%Y-%m-%d %H:%M:%S') if local_pdf_uploaded else None,
            'pdf_uploaded_by': self.pdf_uploaded_by
        }

    def __repr__(self):
        return f'<LaborApplication {self.project_name}>'
