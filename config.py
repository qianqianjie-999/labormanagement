# config.py - 应用程序配置文件

import os

# 获取项目根目录
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """应用程序配置类"""

    # 安全密钥，用于保护表单等
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'

    # 数据库配置
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://labor_app_user:labor_app_password@127.0.0.1:3306/labor_application_db'
    #SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://labor_app_user:labor_app_password@[::1]:3306/labor_application_db'

    # 是否追踪对象修改（关闭以节省性能）
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 上传文件配置
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')  # 上传文件保存目录
    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}  # 允许上传的文件扩展名
    ALLOWED_PDF_EXTENSIONS = {'pdf'}  # 允许上传的 PDF 扩展名
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 最大上传文件大小：16MB

    # PDF 附件配置
    PDF_UPLOAD_FOLDER = os.path.join(basedir, 'uploads', 'signed_pdfs')  # PDF 上传保存目录

    # PDF导出配置
    PDF_EXPORT_FOLDER = os.path.join(basedir, 'exports')
