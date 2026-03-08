# config.py - 应用程序配置文件

import os

# 获取项目根目录
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """应用程序配置类"""

    # 安全密钥，用于保护表单等
    # 生产环境请使用环境变量设置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'

    # 数据库配置
    # 生产环境请使用环境变量或在 .env 文件中配置
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'mysql+pymysql://labor_app_user:labor_app_password@127.0.0.1:3306/labor_application_db'
    )

    # 是否追踪对象修改（关闭以节省性能）
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 上传文件配置
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 最大上传文件大小：16MB

    # PDF 导出配置
    PDF_EXPORT_FOLDER = os.path.join(basedir, 'exports')

    # 日志配置
    LOG_FOLDER = os.path.join(basedir, 'logs')
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# 配置字典，便于动态加载
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
