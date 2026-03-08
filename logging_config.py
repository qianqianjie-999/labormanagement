# logging_config.py - 日志配置模块

import os
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime


def setup_logging(app):
    """
    配置应用程序日志

    Args:
        app: Flask 应用实例
    """
    # 确保日志目录存在
    log_folder = app.config.get('LOG_FOLDER', 'logs')
    os.makedirs(log_folder, exist_ok=True)

    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台日志处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)

    # 文件日志处理器 - 按大小轮转
    file_handler = RotatingFileHandler(
        os.path.join(log_folder, 'app.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # 错误日志处理器 - 单独记录错误
    error_handler = RotatingFileHandler(
        os.path.join(log_folder, 'error.log'),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)

    # 应用日志
    app.logger.addHandler(console_handler)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)
    app.logger.setLevel(logging.DEBUG)

    # SQLAlchemy 日志
    db_logger = logging.getLogger('sqlalchemy.engine')
    db_logger.addHandler(file_handler)
    db_logger.setLevel(logging.WARNING)

    # Werkzeug 日志
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.addHandler(file_handler)
    werkzeug_logger.setLevel(logging.INFO)

    app.logger.info("=" * 50)
    app.logger.info(f"应用启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    app.logger.info(f"日志目录：{log_folder}")
    app.logger.info(f"运行环境：{app.config.get('FLASK_ENV', 'development')}")
    app.logger.info("=" * 50)

    return app.logger
