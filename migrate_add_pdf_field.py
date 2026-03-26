#!/usr/bin/env python3
"""
数据库迁移脚本 - 添加 PDF 附件字段到 labor_applications 表
用于存储签字扫描版 PDF 文件
"""
import sys
import os

# 将当前目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app, db
    from models import User, WorkItem
    print("✅ 模块导入成功")
except ImportError as e:
    print(f"❌ 导入失败：{e}")
    print("当前目录:", os.getcwd())
    print("Python 路径:", sys.path)
    sys.exit(1)

app = create_app()

with app.app_context():
    try:
        from sqlalchemy import inspect, text

        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('labor_applications')]

        print(f"📊 当前 labor_applications 表的字段：{columns}")

        # 检查是否需要添加新字段
        new_columns = {
            'signed_pdf_filename': db.Column(db.String(255)),
            'pdf_uploaded_at': db.Column(db.DateTime),
            'pdf_uploaded_by': db.Column(db.String(50))
        }

        columns_to_add = []
        for col_name, col_def in new_columns.items():
            if col_name not in columns:
                columns_to_add.append(col_name)

        if not columns_to_add:
            print("✅ 所有字段已存在，无需迁移")
        else:
            print(f"正在添加字段：{columns_to_add}")

            # 使用原生 SQL 添加字段
            with db.engine.connect() as conn:
                for col_name in columns_to_add:
                    if col_name == 'signed_pdf_filename':
                        sql = text(f"ALTER TABLE labor_applications ADD COLUMN {col_name} VARCHAR(255)")
                    elif col_name == 'pdf_uploaded_at':
                        sql = text(f"ALTER TABLE labor_applications ADD COLUMN {col_name} DATETIME")
                    elif col_name == 'pdf_uploaded_by':
                        sql = text(f"ALTER TABLE labor_applications ADD COLUMN {col_name} VARCHAR(50)")

                    conn.execute(sql)
                    print(f"✅ 添加字段 {col_name} 成功")

                conn.commit()

            print("🎉 数据库迁移完成！")

        # 验证结果
        columns = [col['name'] for col in inspector.get_columns('labor_applications')]
        print(f"📊 迁移后 labor_applications 表的字段：{columns}")

    except Exception as e:
        print(f"❌ 迁移失败：{e}")
        import traceback
        traceback.print_exc()
