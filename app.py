# app.py - 用工申请管理系统主程序
import json
import os
from datetime import datetime, timedelta,timezone
from io import BytesIO

import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping

# 导入配置和模型
from config import Config
from models import db, User, WorkItem, ApplicationItem, LaborApplication
# 设置一个全局变量来存储参考系数,从json文件加载

# 获取项目根目录的正确路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
print(f"项目根目录: {BASE_DIR}")

# 使用项目根目录下的logs子目录
CONFIG_DIR = os.path.join(BASE_DIR, 'logs')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')

def load_reference_coefficient():
    """从JSON文件加载参考系数"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return float(config.get('reference_coefficient', 0.85))
        else:
            # 如果文件不存在，创建默认配置
            default_config = {"reference_coefficient": 0.85}
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return 0.85
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        return 0.85


def save_reference_coefficient(coefficient):
    """保存参考系数到JSON文件"""
    try:
        config = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)

        config['reference_coefficient'] = coefficient

        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        return True
    except Exception as e:
        print(f"保存配置文件失败: {e}")
        return False


# 设置一个全局变量来存储参考系数
global_reference_coefficient = load_reference_coefficient()


# 全局常量
STATUS_MAPPING = {
    'pending': '待处理',
    'approved': '已批准',
    'rejected': '已拒绝'
}


# 公共函数
def utc_to_beijing(utc_dt):
    """UTC时间转换为北京时间"""
    return utc_dt + timedelta(hours=8) if utc_dt else None


def beijing_to_utc(beijing_dt):
    """北京时间转换为UTC时间"""
    return beijing_dt - timedelta(hours=8) if beijing_dt else None


def format_beijing_time(dt):
    """格式化时间为北京时间字符串"""
    if not dt:
        return '-'
    try:
        # 确保返回字符串格式
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"[WARNING] 时间格式化错误: {e}, dt类型: {type(dt)}, dt值: {dt}")
        return str(dt)  


def get_chinese_status(status):
    """获取状态的中文描述"""
    return STATUS_MAPPING.get(status, status)


# 创建Flask应用实例
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 确保目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PDF_EXPORT_FOLDER'], exist_ok=True)
    # 从JSON文件加载参考系数（去掉原来从配置文件加载的代码）
    global global_reference_coefficient
    print(f"加载参考系数: {global_reference_coefficient}")

    # 添加上下文处理器，让所有模板都能访问参考系数
    @app.context_processor
    def inject_reference_coefficient():
        """将参考系数注入到所有模板中"""
        return dict(current_reference_coefficient=global_reference_coefficient)
    # 初始化数据库
    db.init_app(app)

    # 初始化Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = '请先登录'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # 辅助函数
    def allowed_file(filename):
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

    def get_report_base_stats(start_date=None, end_date=None):
        """获取报表基础统计数据"""
        query = db.session.query(LaborApplication)

        if start_date:
            utc_start = beijing_to_utc(start_date)
            query = query.filter(LaborApplication.created_at >= utc_start)

        if end_date:
            end_date_with_time = datetime.combine(end_date, datetime.max.time())
            utc_end = beijing_to_utc(end_date_with_time)
            query = query.filter(LaborApplication.created_at <= utc_end)

        applications = query.all()

        status_counts = {'pending': 0, 'approved': 0, 'rejected': 0}
        for app in applications:
            status_counts[app.status] += 1

        category_query = db.session.query(
            WorkItem.category,
            db.func.count(ApplicationItem.id).label('usage_count')
        ).join(
            ApplicationItem, WorkItem.id == ApplicationItem.work_item_id
        ).join(
            LaborApplication, ApplicationItem.application_id == LaborApplication.id
        )

        if start_date:
            utc_start = beijing_to_utc(start_date)
            category_query = category_query.filter(LaborApplication.created_at >= utc_start)

        if end_date:
            end_date_with_time = datetime.combine(end_date, datetime.max.time())
            utc_end = beijing_to_utc(end_date_with_time)
            category_query = category_query.filter(LaborApplication.created_at <= utc_end)

        category_query = category_query.group_by(WorkItem.category).order_by(db.desc('usage_count')).limit(5)
        category_results = category_query.all()

        categories = []
        usage_counts = []
        for category, count in category_results:
            if category:
                categories.append(category)
                usage_counts.append(count)

        return {
            'status_counts': status_counts,
            'categories': categories,
            'usage_counts': usage_counts,
            'total_departments': len(set([app.department for app in applications if app.department]))
        }

    def get_overview_stats(start_date=None, end_date=None):
        """获取概览统计数据"""
        query = LaborApplication.query

        if start_date:
            utc_start = beijing_to_utc(start_date)
            query = query.filter(LaborApplication.created_at >= utc_start)

        if end_date:
            end_date_with_time = datetime.combine(end_date, datetime.max.time())
            utc_end = beijing_to_utc(end_date_with_time)
            query = query.filter(LaborApplication.created_at <= utc_end)

        applications = query.all()
        total_applications = len(applications)

        status_counts = {'pending': 0, 'approved': 0, 'rejected': 0}
        total_labor = 0
        departments = set()

        for app in applications:
            status_counts[app.status] += 1
            total_labor += app.total_required_labor or 0
            if app.department:
                departments.add(app.department)

        avg_labor_per_app = total_labor / total_applications if total_applications > 0 else 0

        if start_date and end_date:
            date_range = []
            current_date = start_date
            while current_date <= end_date:
                date_range.append(current_date.strftime('%Y-%m-%d'))
                current_date += timedelta(days=1)

            if len(date_range) > 30:
                date_range = date_range[-30:]
        else:
            end_date_local = datetime.now()
            start_date_local = end_date_local - timedelta(days=29)
            date_range = [(start_date_local + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]

        daily_counts = []
        for date_str in date_range:
            beijing_date = datetime.strptime(date_str, '%Y-%m-%d')
            beijing_start = beijing_date
            beijing_end = beijing_date + timedelta(days=1)

            utc_start = beijing_to_utc(beijing_start)
            utc_end = beijing_to_utc(beijing_end)

            count = LaborApplication.query.filter(
                LaborApplication.created_at >= utc_start,
                LaborApplication.created_at < utc_end
            ).count()
            daily_counts.append(count)

        base_stats = get_report_base_stats(start_date, end_date)

        recent_apps = LaborApplication.query.order_by(LaborApplication.created_at.desc()).limit(10).all()
        applications_data = []
        for app in recent_apps:
            app_dict = app.to_dict()
            app_dict['local_created_at'] = format_beijing_time(app.created_at)
            applications_data.append(app_dict)

        return {
            'success': True,
            'data': {
                'total_applications': total_applications,
                'status_counts': status_counts,
                'total_labor': round(total_labor, 2),
                'avg_labor_per_app': round(avg_labor_per_app, 2),
                'total_departments': base_stats['total_departments'],
                'dates': date_range,
                'counts': daily_counts,
                'categories': base_stats['categories'],
                'usage_counts': base_stats['usage_counts'],
                'applications': applications_data
            }
        }

    def get_trend_stats(start_date=None, end_date=None):
        """获取趋势统计数据"""
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        date_range = []
        current_date = start_date
        while current_date <= end_date:
            date_range.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)

        if len(date_range) > 60:
            date_range = date_range[-60:]

        daily_counts = []
        daily_labor_totals = []

        for date_str in date_range:
            beijing_date = datetime.strptime(date_str, '%Y-%m-%d')
            beijing_start = beijing_date
            beijing_end = beijing_date + timedelta(days=1)

            utc_start = beijing_to_utc(beijing_start)
            utc_end = beijing_to_utc(beijing_end)

            count = LaborApplication.query.filter(
                LaborApplication.created_at >= utc_start,
                LaborApplication.created_at < utc_end
            ).count()

            total_labor_result = db.session.query(
                db.func.sum(LaborApplication.total_required_labor)
            ).filter(
                LaborApplication.created_at >= utc_start,
                LaborApplication.created_at < utc_end
            ).first()

            total_labor = float(total_labor_result[0] or 0)

            daily_counts.append(count)
            daily_labor_totals.append(total_labor)

        base_stats = get_report_base_stats(start_date, end_date)

        return {
            'success': True,
            'data': {
                'dates': date_range,
                'counts': daily_counts,
                'labor_totals': daily_labor_totals,
                'status_counts': base_stats['status_counts'],
                'categories': base_stats['categories'],
                'usage_counts': base_stats['usage_counts']
            }
        }

    def get_department_stats(start_date=None, end_date=None):
        """获取部门统计数据"""
        query = db.session.query(
            LaborApplication.department,
            db.func.count(LaborApplication.id).label('count'),
            db.func.sum(LaborApplication.total_required_labor).label('total_labor')
        )

        if start_date:
            utc_start = beijing_to_utc(start_date)
            query = query.filter(LaborApplication.created_at >= utc_start)

        if end_date:
            end_date_with_time = datetime.combine(end_date, datetime.max.time())
            utc_end = beijing_to_utc(end_date_with_time)
            query = query.filter(LaborApplication.created_at <= utc_end)

        query = query.group_by(LaborApplication.department).order_by(db.desc('total_labor'))
        results = query.all()

        departments = []
        application_counts = []
        labor_totals = []

        for dept, count, total_labor in results:
            if dept:
                departments.append(dept)
                application_counts.append(count)
                labor_totals.append(float(total_labor or 0))

        avg_labor_per_dept = []
        for i, count in enumerate(application_counts):
            if count > 0:
                avg = labor_totals[i] / count
                avg_labor_per_dept.append(round(avg, 2))
            else:
                avg_labor_per_dept.append(0)

        total_apps = sum(application_counts)
        percentages = []
        for count in application_counts:
            if total_apps > 0:
                percentage = (count / total_apps) * 100
                percentages.append(round(percentage, 1))
            else:
                percentages.append(0)

        base_stats = get_report_base_stats(start_date, end_date)

        return {
            'success': True,
            'data': {
                'departments': departments,
                'application_counts': application_counts,
                'labor_totals': labor_totals,
                'avg_labor_per_dept': avg_labor_per_dept,
                'percentages': percentages,
                'status_counts': base_stats['status_counts'],
                'categories': base_stats['categories'],
                'usage_counts': base_stats['usage_counts']
            }
        }

    def get_category_stats(start_date=None, end_date=None):
        """获取工程分类统计数据"""
        query = db.session.query(
            WorkItem.category,
            db.func.count(ApplicationItem.id).label('usage_count'),
            db.func.sum(ApplicationItem.required_labor).label('total_labor'),
            db.func.sum(ApplicationItem.quantity).label('total_quantity')
        ).join(
            ApplicationItem, WorkItem.id == ApplicationItem.work_item_id
        ).join(
            LaborApplication, ApplicationItem.application_id == LaborApplication.id
        )

        if start_date:
            utc_start = beijing_to_utc(start_date)
            query = query.filter(LaborApplication.created_at >= utc_start)

        if end_date:
            end_date_with_time = datetime.combine(end_date, datetime.max.time())
            utc_end = beijing_to_utc(end_date_with_time)
            query = query.filter(LaborApplication.created_at <= utc_end)

        query = query.group_by(WorkItem.category).order_by(db.desc('usage_count'))
        results = query.all()

        categories = []
        usage_counts = []
        labor_totals = []
        quantity_totals = []

        for category, count, labor, quantity in results:
            if category:
                categories.append(category)
                usage_counts.append(count)
                labor_totals.append(float(labor or 0))
                quantity_totals.append(float(quantity or 0))

        avg_labor_per_category = []
        for i, count in enumerate(usage_counts):
            if count > 0:
                avg = labor_totals[i] / count
                avg_labor_per_category.append(round(avg, 2))
            else:
                avg_labor_per_category.append(0)

        avg_quantity_per_category = []
        for i, count in enumerate(usage_counts):
            if count > 0:
                avg = quantity_totals[i] / count
                avg_quantity_per_category.append(round(avg, 2))
            else:
                avg_quantity_per_category.append(0)

        base_stats = get_report_base_stats(start_date, end_date)

        return {
            'success': True,
            'data': {
                'categories': categories,
                'usage_counts': usage_counts,
                'labor_totals': labor_totals,
                'quantity_totals': quantity_totals,
                'avg_labor_per_category': avg_labor_per_category,
                'avg_quantity_per_category': avg_quantity_per_category,
                'status_counts': base_stats['status_counts']
            }
        }

    def generate_excel_sheet(writer, report_type, data):
        """生成Excel工作表"""
        if not data.get('success'):
            raise ValueError("数据获取失败")

        data = data.get('data', {})

        if report_type == 'overview':
            overview_df = pd.DataFrame({
                '统计指标': ['总申请数', '总人工数', '平均人工数', '涉及部门数'],
                '数值': [
                    data.get('total_applications', 0),
                    data.get('total_labor', 0),
                    data.get('avg_labor_per_app', 0),
                    data.get('total_departments', 0)
                ]
            })
            overview_df.to_excel(writer, sheet_name='统计概览', index=False)

            status_counts = data.get('status_counts', {})
            status_df = pd.DataFrame({
                '状态': ['待处理', '已批准', '已拒绝'],
                '数量': [
                    status_counts.get('pending', 0),
                    status_counts.get('approved', 0),
                    status_counts.get('rejected', 0)
                ]
            })
            status_df.to_excel(writer, sheet_name='状态统计', index=False)

            categories = data.get('categories', [])
            usage_counts = data.get('usage_counts', [])
            category_df = pd.DataFrame({
                '工程分类': categories,
                '使用次数': usage_counts
            })
            category_df.to_excel(writer, sheet_name='热门分类', index=False)

            dates = data.get('dates', [])
            counts = data.get('counts', [])
            trend_df = pd.DataFrame({
                '日期': dates,
                '申请数量': counts
            })
            trend_df.to_excel(writer, sheet_name='时间趋势', index=False)

            applications = data.get('applications', [])
            if applications:
                app_records = []
                for app in applications:
                    app_records.append({
                        '申请时间': app.get('local_created_at', ''),
                        '项目名称': app.get('project_name', ''),
                        '申请部门': app.get('department', ''),
                        '申请人': app.get('applicant', ''),
                        '总人工数': app.get('total_required_labor', 0),
                        '状态': get_chinese_status(app.get('status', ''))
                    })
                app_df = pd.DataFrame(app_records)
                app_df.to_excel(writer, sheet_name='最近申请', index=False)

        elif report_type == 'department':
            departments = data.get('departments', [])
            application_counts = data.get('application_counts', [])
            labor_totals = data.get('labor_totals', [])
            percentages = data.get('percentages', [])

            dept_df = pd.DataFrame({
                '部门': departments,
                '申请数量': application_counts,
                '总人工数': labor_totals,
                '占比(%)': percentages
            })
            dept_df.to_excel(writer, sheet_name='部门统计', index=False)

        elif report_type == 'category':
            categories = data.get('categories', [])
            usage_counts = data.get('usage_counts', [])
            labor_totals = data.get('labor_totals', [])
            quantity_totals = data.get('quantity_totals', [])

            category_df = pd.DataFrame({
                '工程分类': categories,
                '使用次数': usage_counts,
                '总人工数': labor_totals,
                '总工程量': quantity_totals
            })
            category_df.to_excel(writer, sheet_name='工程分类统计', index=False)

        elif report_type == 'trend':
            dates = data.get('dates', [])
            counts = data.get('counts', [])
            labor_totals = data.get('labor_totals', [])

            trend_df = pd.DataFrame({
                '日期': dates,
                '申请数量': counts,
                '总人工数': labor_totals
            })
            trend_df.to_excel(writer, sheet_name='趋势分析', index=False)

    def import_from_excel(file_path):
        """从Excel文件导入分部分项工程数据"""
        try:
            df = pd.read_excel(file_path)

            required_columns = ['分部分项代码', '分部分项名称', '单位人工', '计量单位', '所属分类']
            for col in required_columns:
                if col not in df.columns:
                    return {'success': False, 'message': f'Excel文件中缺少必要列: {col}'}

            success_count = 0
            error_count = 0
            errors = []

            for index, row in df.iterrows():
                try:
                    existing_item = WorkItem.query.filter_by(code=row['分部分项代码']).first()

                    if existing_item:
                        existing_item.name = row['分部分项名称']
                        existing_item.labor_coefficient = float(row['单位人工'])
                        existing_item.unit = row['计量单位']
                        existing_item.category = row['所属分类']
                        success_count += 1
                    else:
                        new_item = WorkItem(
                            code=row['分部分项代码'],
                            name=row['分部分项名称'],
                            labor_coefficient=float(row['单位人工']),
                            unit=row['计量单位'],
                            category=row['所属分类']
                        )
                        db.session.add(new_item)
                        success_count += 1

                except Exception as e:
                    error_count += 1
                    errors.append(f"第{index + 2}行错误: {str(e)}")

            db.session.commit()

            return {
                'success': True,
                'message': f'导入完成！成功: {success_count}条，失败: {error_count}条',
                'success_count': success_count,
                'error_count': error_count,
                'errors': errors
            }

        except Exception as e:
            return {'success': False, 'message': f'导入失败: {str(e)}'}

    def generate_pdf_application(application, is_admin=False):
        """生成用工申请PDF文件"""
        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=1.5 * cm,
            rightMargin=1.5 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm
        )

        story = []
        styles = getSampleStyleSheet()

        try:
            font_path = os.path.join(app.static_folder, 'fonts', 'SimSun.ttf')
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('SimSun', font_path))
                pdfmetrics.registerFont(TTFont('SimSun-Bold', font_path))

                addMapping('SimSun', 0, 0, 'SimSun')
                addMapping('SimSun', 1, 0, 'SimSun-Bold')
                chinese_font = 'SimSun'
            else:
                chinese_font = 'Helvetica'
        except Exception as e:
            chinese_font = 'Helvetica'

        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=chinese_font,
            fontSize=16,
            alignment=1,
            spaceAfter=20
        )

        section_style = ParagraphStyle(
            'CustomSection',
            parent=styles['Heading2'],
            fontName=f'{chinese_font}-Bold' if '-Bold' in locals() else chinese_font,
            fontSize=12,
            spaceBefore=15,
            spaceAfter=8
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName=chinese_font,
            fontSize=10,
            leading=12,
            wordWrap='CJK'
        )

        table_style = ParagraphStyle(
            'CustomTable',
            parent=normal_style,
            fontSize=9,
            leading=10,
            wordWrap='CJK'
        )

        long_text_style = ParagraphStyle(
            'CustomLongText',
            parent=table_style,
            fontSize=8,
            leading=9,
            wordWrap='CJK',
            alignment=0
        )

        # 根据用户角色调整列宽
        if is_admin:
            # 管理员：显示完整信息
            col_widths_part3 = [1.2 * cm, 2.5 * cm, 6.0 * cm, 2.0 * cm, 2.0 * cm, 2.0 * cm, 2.3 * cm, 2.3 * cm]
        else:
            # 普通用户：隐藏系数列，增加拟申请用工列
            col_widths_part3 = [1.2 * cm, 2.5 * cm, 6.0 * cm, 2.0 * cm, 2.0 * cm, 2.3 * cm, 2.3 * cm]

        # 标题
        title = "用工申请表（用户版）" if not is_admin else "用工申请表（管理员版）"
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 15))

        # 一、申请部门申请人员
        story.append(Paragraph("一、申请部门及申请人员", section_style))

        dept_col_widths = [3 * cm, 5 * cm, 3 * cm, 7 * cm]

        dept_data = [
            [
                Paragraph('申请部门：', table_style),
                Paragraph(application.department or '', table_style),
                Paragraph('申请人员：', table_style),
                Paragraph(application.applicant or '', table_style)
            ],
            [
                Paragraph('申请日期：', table_style),
                Paragraph(format_beijing_time(application.created_at), table_style),
                Paragraph('项目名称：', table_style),
                Paragraph(application.project_name or '', table_style)
            ]
        ]

        dept_table = Table(dept_data, colWidths=dept_col_widths)
        dept_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('WORDWRAP', (0, 0), (-1, -1), True),
        ]))

        story.append(dept_table)
        story.append(Spacer(1, 15))

        # 二、项目信息
        story.append(Paragraph("二、项目信息", section_style))
        story.append(Paragraph(f"<b>项目名称：</b>{application.project_name}", normal_style))
        story.append(Spacer(1, 8))

        if application.project_description:
            project_data = [
                [
                    Paragraph('<b>项目说明：</b>', table_style),
                    Paragraph(application.project_description or '无', long_text_style)
                ]
            ]

            project_table = Table(project_data, colWidths=[3 * cm, 15 * cm])
            project_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
                ('ALIGN', (1, 0), (1, 0), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, -1), chinese_font),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('WORDWRAP', (0, 0), (-1, -1), True),
            ]))

            story.append(project_table)
        else:
            story.append(Paragraph("<b>项目说明：</b>无", normal_style))

        story.append(Spacer(1, 15))

        # 三、用工计算表格
        story.append(Paragraph("三、用工计算明细", section_style))

        if is_admin:
            # 管理员表格标题
            calc_data = [
                [
                    Paragraph('序号', table_style),
                    Paragraph('分部分项代码', table_style),
                    Paragraph('分部分项名称', table_style),
                    Paragraph('用工系数', table_style),
                    Paragraph('计量单位', table_style),
                    Paragraph('工程量', table_style),
                    Paragraph('系统计算', table_style),
                    Paragraph('用户申请', table_style)
                ]
            ]
        else:
            # 普通用户表格标题（隐藏系数）
            calc_data = [
                [
                    Paragraph('序号', table_style),
                    Paragraph('分部分项代码', table_style),
                    Paragraph('分部分项名称', table_style),
                    Paragraph('计量单位', table_style),
                    Paragraph('工程量', table_style),
                    Paragraph('系统计算', table_style),
                    Paragraph('拟申请用工', table_style)
                ]
            ]

        # 计算明细和合计
        total_labor = 0
        total_user_proposed = 0

        for i, item in enumerate(application.items, 1):
            work_item_data = item.get_work_item_data()

            if work_item_data:
                if is_admin:
                    # 管理员：显示完整信息
                    user_labor_display = item.user_proposed_labor if item.user_proposed_labor else item.required_labor
                    row = [
                        Paragraph(str(i), table_style),
                        Paragraph(work_item_data['code'] or '', table_style),
                        Paragraph(work_item_data['name'] or '', long_text_style),
                        Paragraph(f"{work_item_data['labor_coefficient']:.2f}", table_style),
                        Paragraph(work_item_data['unit'] or '', table_style),
                        Paragraph(f"{item.quantity:.2f}", table_style),
                        Paragraph(f"{item.required_labor:.2f}", table_style),
                        Paragraph(f"{user_labor_display:.2f}", table_style)
                    ]
                    total_user_proposed += float(user_labor_display)
                else:
                    # 普通用户：隐藏系数
                    user_proposed_display = f"{item.user_proposed_labor:.2f}" if item.user_proposed_labor else "***"
                    row = [
                        Paragraph(str(i), table_style),
                        Paragraph(work_item_data['code'] or '', table_style),
                        Paragraph(work_item_data['name'] or '', long_text_style),
                        Paragraph(work_item_data['unit'] or '', table_style),
                        Paragraph(f"{item.quantity:.2f}", table_style),
                        Paragraph("***", table_style),  # 隐藏系统计算
                        Paragraph(user_proposed_display, table_style)
                    ]
                    # 如果用户填写了拟申请用工，累加它
                    if item.user_proposed_labor:
                        total_user_proposed += float(item.user_proposed_labor)
                    else:
                        # 如果没有填写，累加系统计算值（对普通用户显示星号，但计算时用系统值）
                        total_user_proposed += float(item.required_labor)

                calc_data.append(row)
                total_labor += float(item.required_labor)

        # 计算季节系数
        beijing_time = utc_to_beijing(application.created_at)
        month = beijing_time.month

        if month in [3, 4, 5]:
            season_coefficient = 1.0
            season_name = "春季"
        elif month in [6, 7, 8]:
            season_coefficient = 1.01
            season_name = "夏季"
        elif month in [9, 10, 11]:
            season_coefficient = 1.0
            season_name = "秋季"
        else:
            season_coefficient = 1.02
            season_name = "冬季"

        # 根据用户类型计算调整后的总用工
        if is_admin:
            # 管理员：系统计算合计 × 季节系数
            adjusted_total_labor = total_labor * season_coefficient
            # 用户申请合计 × 季节系数
            adjusted_total_user_proposed = total_user_proposed * season_coefficient
        else:
            # 普通用户：用户申请合计 × 季节系数
            adjusted_total_user_proposed = total_user_proposed * season_coefficient

        # 添加合计行
        if is_admin:
            # 管理员版本
            # 系统计算合计行
            calc_data.append([
                '', '', '', '', '',
                Paragraph(f'<b>系统计算合计：{total_labor:.2f}</b>', table_style),
                '',
                ''
            ])

            # 用户申请合计行
            calc_data.append([
                '', '', '', '', '',
                Paragraph(f'<b>用户申请合计：{total_user_proposed:.2f}</b>', table_style),
                '',
                ''
            ])

            # 季节系数行
            calc_data.append([
                Paragraph(f'<b>季节系数（{season_name} ×{season_coefficient}）：</b>', table_style),
                '', '', '', '', '', '', ''
            ])

            # 调整后系统计算行
            calc_data.append([
                Paragraph(f'<b>季节系数调整后系统计算：{adjusted_total_labor:.2f}</b>', table_style),
                '', '', '', '', '','',''
            ])

            # 调整后用户申请行
            calc_data.append([
                Paragraph(f'<b>季节系数调整后用户申请：{adjusted_total_user_proposed:.2f}</b>', table_style),
                '', '', '', '', '','',''
            ])
        else:
            # 普通用户版本
            # 用户申请合计行（显示为"您申请合计"）
            calc_data.append([
                '', '', '',
                Paragraph(f'<b>您申请合计：{total_user_proposed:.2f}</b>', table_style),
                '','',''
            ])

            # 季节系数行
            calc_data.append([
                Paragraph(f'<b>季节系数（{season_name} ×{season_coefficient}）：</b>', table_style),
                '', '', '', '', '', ''
            ])

            # 调整后总用工行
            calc_data.append([
                Paragraph(f'<b>季节系数调整后总用工：{adjusted_total_user_proposed:.2f}</b>', table_style),
                '', '', '', '','',''
            ])

        calc_table = Table(calc_data, colWidths=col_widths_part3, repeatRows=1)
        total_rows = len(calc_data)

        # 设置表格样式
        calc_table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F81BD')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), f'{chinese_font}-Bold' if '-Bold' in locals() else chinese_font),
            ('FONTSIZE', (0, 0), (-1, 0), 9),

            ('BACKGROUND', (0, 1), (-1, -2), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -2), colors.black),
            ('ALIGN', (0, 1), (0, -2), 'CENTER'),
            ('ALIGN', (1, 1), (1, -2), 'LEFT'),
            ('ALIGN', (3, 1), (3, -2), 'RIGHT'),
            ('ALIGN', (5, 1), (-1, -2), 'RIGHT'),
            ('FONTNAME', (0, 1), (-1, -2), chinese_font),
            ('FONTSIZE', (0, 1), (-1, -2), 8),

            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),

            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),

            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('WORDWRAP', (0, 0), (-1, -1), True),
        ])

        # 根据用户类型添加合并单元格和特殊样式
        if is_admin:
            # 管理员版本的特殊样式
            system_sum_row = total_rows - 5
            user_sum_row = total_rows - 4
            season_row = total_rows - 3
            adjusted_system_row = total_rows - 2
            adjusted_user_row = total_rows - 1

            # 合并单元格
            calc_table_style.add('SPAN', (5, system_sum_row), (6, system_sum_row))  # 系统计算合计
            calc_table_style.add('SPAN', (5, user_sum_row), (6, user_sum_row))  # 用户申请合计
            calc_table_style.add('SPAN', (0, season_row), (7, season_row))  # 季节系数
            calc_table_style.add('SPAN', (0, adjusted_system_row), (6, adjusted_system_row))  # 调整后系统计算
            calc_table_style.add('SPAN', (0, adjusted_user_row), (6, adjusted_user_row))  # 调整后用户申请

            # 特殊样式
            calc_table_style.add('BACKGROUND', (5, system_sum_row), (6, system_sum_row), colors.HexColor('#D9D9D9'))
            calc_table_style.add('FONTNAME', (5, system_sum_row), (6, system_sum_row), f'{chinese_font}-Bold')

            calc_table_style.add('BACKGROUND', (5, user_sum_row), (7, user_sum_row), colors.HexColor('#FFF2CC'))
            calc_table_style.add('FONTNAME', (5, user_sum_row), (7, user_sum_row), f'{chinese_font}-Bold')

            calc_table_style.add('BACKGROUND', (0, season_row), (0, season_row), colors.HexColor('#E8F4FD'))
            calc_table_style.add('FONTNAME', (0, season_row), (0, season_row), f'{chinese_font}-Bold')

            calc_table_style.add('BACKGROUND', (0, adjusted_system_row), (6, adjusted_system_row),
                                 colors.HexColor('#4F81BD'))
            calc_table_style.add('TEXTCOLOR', (0, adjusted_system_row), (6, adjusted_system_row), colors.white)
            calc_table_style.add('FONTNAME', (0, adjusted_system_row), (6, adjusted_system_row), f'{chinese_font}-Bold')

            calc_table_style.add('BACKGROUND', (0, adjusted_user_row), (6, adjusted_user_row),
                                 colors.HexColor('#FF9900'))
            calc_table_style.add('TEXTCOLOR', (0, adjusted_user_row), (6, adjusted_user_row), colors.white)
            calc_table_style.add('FONTNAME', (0, adjusted_user_row), (6, adjusted_user_row), f'{chinese_font}-Bold')
        else:
            # 普通用户版本的特殊样式
            user_sum_row = total_rows - 3
            season_row = total_rows - 2
            adjusted_row = total_rows - 1

            # 合并单元格
            calc_table_style.add('SPAN', (3, user_sum_row), (5, user_sum_row))  # 您申请合计
            calc_table_style.add('SPAN', (0, season_row), (6, season_row))  # 季节系数
            calc_table_style.add('SPAN', (0, adjusted_row), (5, adjusted_row))  # 调整后总用工

            # 特殊样式
            calc_table_style.add('BACKGROUND', (3, user_sum_row), (6, user_sum_row), colors.HexColor('#FFF2CC'))
            calc_table_style.add('FONTNAME', (3, user_sum_row), (6, user_sum_row), f'{chinese_font}-Bold')

            calc_table_style.add('BACKGROUND', (0, season_row), (0, season_row), colors.HexColor('#E8F4FD'))
            calc_table_style.add('FONTNAME', (0, season_row), (0, season_row), f'{chinese_font}-Bold')

            calc_table_style.add('BACKGROUND', (0, adjusted_row), (5, adjusted_row), colors.HexColor('#4F81BD'))
            calc_table_style.add('TEXTCOLOR', (0, adjusted_row), (5, adjusted_row), colors.white)
            calc_table_style.add('FONTNAME', (0, adjusted_row), (5, adjusted_row), f'{chinese_font}-Bold')

        calc_table.setStyle(calc_table_style)
        story.append(calc_table)
        story.append(Spacer(1, 15))

        # 四、工人名单
        story.append(Paragraph("四、工人名单及其它说明", section_style))

        if application.worker_names and application.worker_names.strip():
            worker_data = [
                [Paragraph('<b>工人名单及其它说明：</b>', table_style)],
                [Paragraph(application.worker_names, long_text_style)]
            ]

            worker_table = Table(worker_data, colWidths=[18 * cm])
            worker_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, -1), chinese_font),
                ('FONTSIZE', (0, 0), (0, 0), 9),
                ('FONTSIZE', (0, 1), (0, 1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('WORDWRAP', (0, 0), (-1, -1), True),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))

            story.append(worker_table)
        else:
            no_worker_data = [
                [Paragraph('<b>工人名单及其它说明：</b>', table_style)],
                [Paragraph('无', long_text_style)]
            ]

            no_worker_table = Table(no_worker_data, colWidths=[18 * cm])
            no_worker_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, -1), chinese_font),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('WORDWRAP', (0, 0), (-1, -1), True),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(no_worker_table)

        story.append(Spacer(1, 20))

        # 五、审批信息
        story.append(Paragraph("五、审批信息", section_style))

        chinese_status = get_chinese_status(application.status)
        approval_col_widths = [3 * cm, 15 * cm]

        # 格式化审批时间
        approval_time_str = format_beijing_time(application.approval_time) if application.approval_time else '-'

        approval_data = [
            [Paragraph('审批状态：', table_style), Paragraph(chinese_status, table_style)],
            [Paragraph('审批人：', table_style), Paragraph(application.approved_by or '待审批', table_style)],
            [Paragraph('审批时间：', table_style), Paragraph(approval_time_str, table_style)],
            [Paragraph('审批意见：', table_style), Paragraph(application.approval_comment or '无', long_text_style)],
        ]

        # 如果是管理员并且有审批后的人工数，显示审批后人工
        if is_admin and application.approved_labor:
            approval_data.append([
                Paragraph('审批后人工：', table_style),
                Paragraph(f"{application.approved_labor:.2f}", table_style)
            ])

        approval_table = Table(approval_data, colWidths=approval_col_widths)
        approval_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, -1), chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('WORDWRAP', (0, 0), (-1, -1), True),
        ]))

        story.append(approval_table)
        story.append(Spacer(1, 10))

        # 页脚
        user_type = "管理员" if is_admin else "普通用户"
        footer_text = f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 用户类型：{user_type}"
        story.append(Paragraph(footer_text, ParagraphStyle(
            'Footer',
            parent=normal_style,
            fontSize=8,
            alignment=2,
            textColor=colors.grey
        )))

        doc.build(story)
        pdf_content = buffer.getvalue()
        buffer.close()

        return pdf_content

    # ==================== 路由定义 ====================

    # 登录页面
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            if current_user.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_index'))

        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            remember = request.form.get('remember', False)

            if not username or not password:
                flash('请输入用户名和密码', 'error')
                return render_template('login.html')

            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                if not user.is_active:
                    flash('该账户已被禁用，请联系管理员', 'error')
                    return render_template('login.html')

                user.update_last_login()
                login_user(user, remember=remember)

                flash('登录成功！', 'success')

                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)

                if user.is_admin:
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('user_index'))
            else:
                flash('用户名或密码错误', 'error')

        return render_template('login.html')
    # 首页重定向到登录页面
    @app.route('/')
    def index():
        """网站首页，重定向到登录页面"""
        return redirect(url_for('login'))
    # 登出
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    @app.route('/admin/get-reference-coefficient')
    @login_required
    def get_reference_coefficient():
        """获取当前参考系数"""
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': '权限不足'}), 403

        global global_reference_coefficient
        return jsonify({
            'success': True,
            'coefficient': global_reference_coefficient
        })

    @app.route('/admin/update-reference-coefficient', methods=['POST'])
    @login_required
    def update_reference_coefficient():
        """更新参考系数"""
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': '权限不足'}), 403

        try:
            data = request.json
            new_coefficient = float(data.get('coefficient', 0.85))

            # 验证范围
            if new_coefficient < 0.7 or new_coefficient > 1.0:
                return jsonify({
                    'success': False,
                    'message': f'参考系数必须在0.7-1.0之间'
                }), 400

                # 保存到JSON文件
            if save_reference_coefficient(new_coefficient):
                global global_reference_coefficient
                global_reference_coefficient = new_coefficient

                return jsonify({
                    'success': True,
                    'message': f'参考系数已更新为 {new_coefficient}',
                    'coefficient': new_coefficient
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '保存配置文件失败'
                }), 500

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    # 管理员仪表板
    @app.route('/admin')
    @login_required
    def admin_dashboard():
        if not current_user.is_admin:
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('user_index'))

        total_items = WorkItem.query.count()
        total_applications = LaborApplication.query.count()
        pending_applications = LaborApplication.query.filter_by(status='pending').count()

        return render_template('admin/dashboard.html',
                               total_items=total_items,
                               total_applications=total_applications,
                               pending_applications=pending_applications)

    # 分部分项工程管理
    @app.route('/admin/items', methods=['GET'])
    @login_required
    def admin_items():
        if not current_user.is_admin:
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('user_index'))

        items = WorkItem.query.all()
        return render_template('admin/items.html', items=items)

    @app.route('/api/admin/items', methods=['POST'])
    @login_required
    def api_add_item():
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': '权限不足'}), 403

        try:
            code = request.form.get('code')
            name = request.form.get('name')
            labor_coefficient = float(request.form.get('labor_coefficient'))
            unit = request.form.get('unit')
            category = request.form.get('category')

            if not all([code, name, unit, category]):
                return jsonify({'success': False, 'message': '所有字段都是必填的'}), 400

            existing_item = WorkItem.query.filter_by(code=code).first()
            if existing_item:
                return jsonify({'success': False, 'message': '分部分项代码已存在'}), 400

            new_item = WorkItem(
                code=code,
                name=name,
                labor_coefficient=labor_coefficient,
                unit=unit,
                category=category
            )

            db.session.add(new_item)
            db.session.commit()

            return jsonify({
                'success': True,
                'message': '添加成功',
                'item': new_item.to_dict()
            })

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/admin/items/<int:item_id>', methods=['PUT'])
    @login_required
    def api_update_item(item_id):
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': '权限不足'}), 403

        try:
            item = WorkItem.query.get_or_404(item_id)

            data = request.json
            item.code = data.get('code', item.code)
            item.name = data.get('name', item.name)
            item.labor_coefficient = float(data.get('labor_coefficient', item.labor_coefficient))
            item.unit = data.get('unit', item.unit)
            item.category = data.get('category', item.category)

            db.session.commit()

            return jsonify({
                'success': True,
                'message': '更新成功',
                'item': item.to_dict()
            })

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/admin/items/<int:item_id>', methods=['DELETE'])
    @login_required
    def api_delete_item(item_id):
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': '权限不足'}), 403

        try:
            item = WorkItem.query.get(item_id)
            if not item:
                return jsonify({'success': False, 'message': '分部分项工程不存在'}), 404

            application_count = ApplicationItem.query.filter_by(work_item_id=item_id).count()
            if application_count > 0:
                return jsonify({
                    'success': False,
                    'message': f'该分部分项已有 {application_count} 条申请记录，无法删除'
                }), 400

            db.session.delete(item)
            db.session.commit()

            return jsonify({
                'success': True,
                'message': '删除成功'
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500

    # Excel导入
    @app.route('/admin/import', methods=['GET', 'POST'])
    @login_required
    def admin_import():
        if not current_user.is_admin:
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('user_index'))

        if request.method == 'POST':
            if 'file' not in request.files:
                flash('没有选择文件', 'error')
                return redirect(request.url)

            file = request.files['file']

            if file.filename == '':
                flash('没有选择文件', 'error')
                return redirect(request.url)

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                result = import_from_excel(filepath)

                if result['success']:
                    flash(result['message'], 'success')
                    if result.get('errors'):
                        for error in result['errors'][:5]:
                            flash(error, 'warning')
                else:
                    flash(result['message'], 'error')

                os.remove(filepath)
                return redirect(url_for('admin_items'))
            else:
                flash('文件类型不支持，请上传Excel文件(.xlsx, .xls)', 'error')

        return render_template('admin/import.html')

    @app.route('/api/items', methods=['GET'])
    def api_get_items():
        items = WorkItem.query.all()
        return jsonify({
            'success': True,
            'items': [item.to_dict() for item in items]
        })

    # 用户主页
    @app.route('/user')
    @login_required
    def user_index():
        return render_template('user/index.html')

    # 新建用工申请
    @app.route('/user/apply', methods=['GET'])
    @login_required
    def user_apply():
        items = WorkItem.query.all()
        return render_template('user/apply.html', items=items)

    @app.route('/user/apply', methods=['POST'])
    @login_required
    def user_apply_submit():
        try:
            department = request.form.get('department')
            applicant = current_user.display_name
            project_name = request.form.get('project_name')
            project_description = request.form.get('project_description', '')
            worker_names = request.form.get('worker_names', '')

            work_items_json = request.form.get('work_items', '[]')
            work_items_data = json.loads(work_items_json)

            application = LaborApplication(
                department=department,
                applicant=applicant,
                project_name=project_name,
                project_description=project_description,
                worker_names=worker_names,
                user_id=current_user.id
            )

            total_labor = 0
            total_user_proposed = 0

            for item_data in work_items_data:
                work_item_id = item_data.get('work_item_id')
                quantity = float(item_data.get('quantity', 0))
                user_proposed_labor = float(item_data.get('user_proposed_labor', 0))

                if work_item_id and quantity > 0:
                    work_item = WorkItem.query.get(work_item_id)
                    if work_item:
                        app_item = ApplicationItem(
                            work_item_id=work_item_id,
                            quantity=quantity,
                            work_item=work_item,
                            user_proposed_labor=user_proposed_labor if user_proposed_labor > 0 else None
                        )
                        application.items.append(app_item)
                        total_labor += app_item.required_labor
                        total_user_proposed += user_proposed_labor if user_proposed_labor > 0 else app_item.required_labor

            application.total_required_labor = total_labor
            application.total_user_proposed = total_user_proposed  # 新增：用户申请的总人工

            db.session.add(application)
            db.session.commit()

            flash(f'申请提交成功！系统计算总人工：***，您申请总人工：{total_user_proposed:.2f}', 'success')
            return redirect(url_for('user_apply_history'))

        except Exception as e:
            flash(f'提交失败：{str(e)}', 'error')
            return redirect(url_for('user_apply'))

    # 修改用工申请页面
    @app.route('/user/apply/edit/<int:application_id>', methods=['GET'])
    @login_required
    def user_apply_edit(application_id):
        """修改用工申请页面"""
        application = LaborApplication.query.get_or_404(application_id)

        # 检查权限
        if not current_user.is_admin and application.applicant != current_user.display_name:
            flash('您没有权限修改此申请', 'error')
            return redirect(url_for('user_apply_history'))

        # 检查状态：只有未批准的申请可以修改
        if application.status == 'approved':
            flash('已批准的申请不能修改', 'error')
            return redirect(url_for('user_apply_history'))

        items = WorkItem.query.all()
        return render_template('user/apply_edit.html',
                               application=application,
                               items=items,
                               current_application_id=application_id)

    # 更新用工申请API - 这是缺失的函数，需要添加
    @app.route('/api/application/<int:application_id>', methods=['PUT'])
    @login_required
    def api_update_application(application_id):
        """更新用工申请API接口"""
        try:
            application = LaborApplication.query.get_or_404(application_id)

            # 检查权限
            if not current_user.is_admin and application.applicant != current_user.display_name:
                return jsonify({
                    'success': False,
                    'message': '无权修改此申请'
                }), 403

            # 检查状态：只有未批准的申请可以修改
            if application.status == 'approved':
                return jsonify({
                    'success': False,
                    'message': '已批准的申请不能修改'
                }), 400

            # 获取表单数据
            data = request.json
            department = data.get('department')
            project_name = data.get('project_name')
            project_description = data.get('project_description', '')
            worker_names = data.get('worker_names', '')
            work_items_data = data.get('work_items', [])

            # 验证数据
            if not all([department, project_name]):
                return jsonify({'success': False, 'message': '部门、项目名称是必填的'}), 400

            # 更新申请信息
            application.department = department
            application.project_name = project_name
            application.project_description = project_description
            application.worker_names = worker_names

            # 删除旧的明细项
            for item in application.items:
                db.session.delete(item)

            total_labor = 0
            total_user_proposed = 0

            # 添加新的明细项（包含快照）
            for item_data in work_items_data:
                work_item_id = item_data.get('work_item_id')
                quantity = float(item_data.get('quantity', 0))
                user_proposed_labor = float(item_data.get('user_proposed_labor', 0))

                if work_item_id and quantity > 0:
                    work_item = WorkItem.query.get(work_item_id)
                    if work_item:
                        app_item = ApplicationItem(
                            work_item_id=work_item_id,
                            quantity=quantity,
                            work_item=work_item,
                            user_proposed_labor=user_proposed_labor if user_proposed_labor > 0 else None
                        )
                        application.items.append(app_item)
                        total_labor += app_item.required_labor
                        total_user_proposed += user_proposed_labor if user_proposed_labor > 0 else app_item.required_labor

            # 设置总人工数
            application.total_required_labor = total_labor
            application.total_user_proposed = total_user_proposed
            application.status = 'pending'  # 修改后重置为待处理状态

            db.session.commit()

            return jsonify({
                'success': True,
                'message': '申请更新成功',
                'total_labor': total_labor,
                'total_user_proposed': total_user_proposed
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'更新失败: {str(e)}'
            }), 500

    # 检查申请是否可以编辑
    @app.route('/api/application/<int:application_id>/can-edit', methods=['GET'])
    @login_required
    def api_can_edit_application(application_id):
        """检查申请是否可以编辑API接口"""
        try:
            application = LaborApplication.query.get_or_404(application_id)

            # 检查权限
            if not current_user.is_admin and application.applicant != current_user.display_name:
                return jsonify({
                    'can_edit': False,
                    'message': '无权编辑此申请'
                })

            # 检查状态：只有未批准的申请可以编辑
            if application.status == 'approved':
                return jsonify({
                    'can_edit': False,
                    'message': '已批准的申请不能编辑'
                })

            return jsonify({
                'can_edit': True,
                'message': '可以编辑'
            })

        except Exception as e:
            return jsonify({
                'can_edit': False,
                'message': f'检查失败: {str(e)}'
            })

    # 计算所需人工数API
    @app.route('/api/calculate', methods=['POST'])
    def api_calculate():
        try:
            data = request.json
            work_items = data.get('work_items', [])

            if not work_items:
                return jsonify({'success': False, 'message': '请添加分部分项工程'}), 400

            total_labor = 0
            items_detail = []

            for item_data in work_items:
                work_item_id = item_data.get('work_item_id')
                quantity = float(item_data.get('quantity', 0))

                if work_item_id and quantity > 0:
                    work_item = WorkItem.query.get(work_item_id)
                    if work_item:
                        required_labor = quantity * work_item.labor_coefficient
                        total_labor += required_labor

                        items_detail.append({
                            'work_item': work_item.to_dict(),
                            'quantity': quantity,
                            'required_labor': required_labor
                        })

            return jsonify({
                'success': True,
                'total_labor': total_labor,
                'items': items_detail
            })

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # 申请历史
    @app.route('/user/history')
    @login_required
    def user_apply_history():
        if current_user.is_admin:
            applications = LaborApplication.query.order_by(LaborApplication.created_at.desc()).all()
        else:
            applications = LaborApplication.query.filter_by(user_id=current_user.id) \
                .order_by(LaborApplication.created_at.desc()).all()

        for app in applications:
            app.local_created_at = format_beijing_time(app.created_at)
        return render_template('user/history.html', applications=applications)

    @app.route('/api/application/<int:application_id>', methods=['GET'])
    @login_required
    def api_get_application(application_id):
        try:
            application = LaborApplication.query.get_or_404(application_id)

            if not current_user.is_admin and application.applicant != current_user.display_name:
                return jsonify({
                    'success': False,
                    'message': '无权查看此申请'
                }), 403

            # 根据用户角色决定是否隐藏系数
            hide_coefficient = not current_user.is_admin
            app_dict = application.to_dict(hide_coefficient)
            app_dict['local_created_at'] = format_beijing_time(application.created_at)

            return jsonify({
                'success': True,
                'application': app_dict
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'获取申请详情失败: {str(e)}'
            }), 500

    # 审批API - 保留第一个定义，删除第二个重复的定义
    @app.route('/api/application/<int:application_id>/status', methods=['PUT'])
    @login_required
    def api_update_application_status(application_id):
        """更新申请状态API接口"""
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': '权限不足'}), 403

        try:
            application = LaborApplication.query.get_or_404(application_id)

            data = request.json
            new_status = data.get('status')
            approval_comment = data.get('approval_comment', '')
            approved_labor = data.get('approved_labor')

            if new_status not in ['pending', 'approved', 'rejected']:
                return jsonify({
                    'success': False,
                    'message': '无效的状态值'
                }), 400

            # 重要：检查是否允许状态转换
            # 规则1: 已批准的申请不能再被修改状态
            if application.status == 'approved':
                return jsonify({
                    'success': False,
                    'message': '已批准的申请不能再修改状态'
                }), 400

            # 规则2: 其他状态可以任意转换
            application.status = new_status

            # 记录审批信息
            if new_status in ['approved', 'rejected']:
                application.approved_by = current_user.display_name
                application.approval_comment = approval_comment
                application.approval_time = datetime.now()

                if new_status == 'approved' and approved_labor is not None:
                    application.approved_labor = float(approved_labor)
            else:
                # 如果状态改回pending，清空审批信息
                application.approved_by = None
                application.approval_comment = None
                application.approval_time = None
                application.approved_labor = None

            db.session.commit()

            chinese_status = get_chinese_status(new_status)
            return jsonify({
                'success': True,
                'message': f'申请状态已更新为 {chinese_status}'
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'更新状态失败: {str(e)}'
            }), 500

    # 用户管理
    @app.route('/admin/users')
    @login_required
    def admin_users():
        if not current_user.is_admin:
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('user_index'))

        users = User.query.order_by(User.created_at.desc()).all()
        return render_template('admin/users.html', users=users)

    @app.route('/api/admin/users', methods=['POST'])
    @login_required
    def api_add_user():
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': '权限不足'}), 403

        try:
            username = request.form.get('username')
            display_name = request.form.get('display_name')
            password = request.form.get('password')
            email = request.form.get('email', '')
            department = request.form.get('department', '')
            is_admin = request.form.get('is_admin') == 'true'

            if not all([username, display_name, password]):
                return jsonify({'success': False, 'message': '用户名、显示名称和密码是必填的'}), 400

            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                return jsonify({'success': False, 'message': '用户名已存在'}), 400

            new_user = User(
                username=username,
                display_name=display_name,
                password=password,
                email=email,
                department=department,
                is_admin=is_admin
            )

            db.session.add(new_user)
            db.session.commit()

            return jsonify({
                'success': True,
                'message': '用户添加成功',
                'user': new_user.to_dict()
            })

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
    @login_required
    def api_update_user(user_id):
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': '权限不足'}), 403

        try:
            user = User.query.get_or_404(user_id)

            data = request.json
            user.display_name = data.get('display_name', user.display_name)
            user.email = data.get('email', user.email)
            user.department = data.get('department', user.department)
            user.is_admin = data.get('is_admin', user.is_admin)
            user.is_active = data.get('is_active', user.is_active)

            new_password = data.get('new_password')
            if new_password:
                user.set_password(new_password)

            db.session.commit()

            return jsonify({
                'success': True,
                'message': '用户更新成功',
                'user': user.to_dict()
            })

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
    @login_required
    def api_delete_user(user_id):
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': '权限不足'}), 403

        try:
            if user_id == current_user.id:
                return jsonify({'success': False, 'message': '不能删除自己的账户'}), 400

            user = User.query.get_or_404(user_id)

            application_count = LaborApplication.query.filter_by(user_id=user_id).count()
            if application_count > 0:
                return jsonify({
                    'success': False,
                    'message': f'该用户有 {application_count} 条申请记录，无法删除'
                }), 400

            db.session.delete(user)
            db.session.commit()

            return jsonify({
                'success': True,
                'message': '用户删除成功'
            })

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/admin/users/<int:user_id>/reset-password', methods=['POST'])
    @login_required
    def api_reset_user_password(user_id):
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': '权限不足'}), 403

        try:
            user = User.query.get_or_404(user_id)

            data = request.json
            new_password = data.get('new_password')

            if not new_password:
                return jsonify({'success': False, 'message': '新密码不能为空'}), 400

            user.set_password(new_password)
            db.session.commit()

            return jsonify({
                'success': True,
                'message': '密码重置成功'
            })

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # 统计报表
    @app.route('/admin/reports')
    @login_required
    def admin_reports():
        if not current_user.is_admin:
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('user_index'))

        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        return render_template('admin/reports.html',
                               start_date=start_date.strftime('%Y-%m-%d'),
                               end_date=end_date.strftime('%Y-%m-%d'))

    # 修改PDF导出路由
    @app.route('/export/pdf/<int:application_id>')
    @login_required
    def export_pdf(application_id):
        application = LaborApplication.query.get_or_404(application_id)

        # 根据当前用户角色生成不同版本的PDF
        pdf_content = generate_pdf_application(application, current_user.is_admin)

        user_type = "admin" if current_user.is_admin else "user"
        filename = f"用工申请_{application.project_name}_{user_type}_{application.created_at.strftime('%Y%m%d_%H%M%S')}.pdf"

        return send_file(
            BytesIO(pdf_content),
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )

    # 用户修改密码
    @app.route('/change-password', methods=['GET', 'POST'])
    @login_required
    def change_password():
        if request.method == 'POST':
            old_password = request.form.get('old_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if not all([old_password, new_password, confirm_password]):
                flash('请填写所有字段', 'error')
                return render_template('change_password.html')

            if new_password != confirm_password:
                flash('新密码两次输入不一致', 'error')
                return render_template('change_password.html')

            if not current_user.check_password(old_password):
                flash('原密码错误', 'error')
                return render_template('change_password.html')

            try:
                current_user.set_password(new_password)
                db.session.commit()

                flash('密码修改成功！', 'success')
                return redirect(url_for('user_index'))
            except Exception as e:
                flash(f'密码修改失败: {str(e)}', 'error')
                db.session.rollback()
                return render_template('change_password.html')

        return render_template('change_password.html')

    # 获取报表数据API
    @app.route('/api/admin/reports/data')
    @login_required
    def api_get_report_data():
        if not current_user.is_admin:
            return jsonify({'success': False, 'message': '权限不足'}), 403

        try:
            report_type = request.args.get('type', 'overview')
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')

            start_date = None
            end_date = None

            if start_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                except ValueError:
                    return jsonify({'success': False, 'message': '开始日期格式错误'}), 400

            if end_date_str:
                try:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                except ValueError:
                    return jsonify({'success': False, 'message': '结束日期格式错误'}), 400

            if report_type == 'overview':
                result = get_overview_stats(start_date, end_date)
            elif report_type == 'department':
                result = get_department_stats(start_date, end_date)
            elif report_type == 'category':
                result = get_category_stats(start_date, end_date)
            elif report_type == 'trend':
                result = get_trend_stats(start_date, end_date)
            else:
                return jsonify({'success': False, 'message': '无效的报表类型'}), 400

            return jsonify(result)

        except Exception as e:
            app.logger.error(f"获取报表数据失败: {str(e)}")
            return jsonify({'success': False, 'message': f'获取数据失败: {str(e)}'}), 500

    # 导出报表为Excel
    @app.route('/admin/reports/export')
    @login_required
    def export_report():
        if not current_user.is_admin:
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('user_index'))

        try:
            report_type = request.args.get('type', 'overview')
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')

            start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None

            if report_type == 'overview':
                data = get_overview_stats(start_date, end_date)
                filename = f"统计概览_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            elif report_type == 'department':
                data = get_department_stats(start_date, end_date)
                filename = f"部门统计_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            elif report_type == 'category':
                data = get_category_stats(start_date, end_date)
                filename = f"工程分类统计_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            elif report_type == 'trend':
                data = get_trend_stats(start_date, end_date)
                filename = f"趋势分析_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            else:
                flash('无效的报表类型', 'error')
                return redirect(url_for('admin_reports'))

            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                generate_excel_sheet(writer, report_type, data)

            buffer.seek(0)

            return send_file(
                buffer,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

        except Exception as e:
            flash(f'导出失败: {str(e)}', 'error')
            return redirect(url_for('admin_reports'))

    return app


# 初始化数据库
def initialize_database(app):
    with app.app_context():
        try:
            db.drop_all()
            db.create_all()
            print("数据库表重新创建成功")

            if not User.query.first():
                admin_user = User(
                    username='admin',
                    display_name='系统管理员',
                    password='admin123',
                    email='admin@example.com',
                    department='系统管理部',
                    is_admin=True
                )

                user1 = User(
                    username='user1',
                    display_name='张三',
                    password='user123',
                    email='user1@example.com',
                    department='工程一部',
                    is_admin=False
                )

                db.session.add(admin_user)
                db.session.add(user1)
                db.session.commit()

                print("默认用户创建成功")
                print(f"管理员账号: admin / admin123")
                print(f"普通用户账号: user1 / user123")

        except Exception as e:
            print(f"数据库初始化失败: {e}")
            db.session.rollback()


# 主程序入口
if __name__ == '__main__':
    app = create_app()

    print("启动用工申请管理系统...")
    print("管理员访问: http://localhost:5000/login")
    print("用户名: admin (管理员) 或 user1 (普通用户)")

    app.run(debug=True, host='0.0.0.0', port=5000)
