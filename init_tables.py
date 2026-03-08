#!/usr/bin/env python3
import sys
import os

# 将当前目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app, db
    from models import User, WorkItem
    print("✅ 模块导入成功")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("当前目录:", os.getcwd())
    print("Python 路径:", sys.path)
    sys.exit(1)

app = create_app()

with app.app_context():
    try:
        # 创建所有表
        db.create_all()
        print("✅ 数据库表创建成功！")
        
        # 检查表
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"📊 已创建的表: {tables}")
        
        # 检查是否已有用户
        user_count = User.query.count()
        print(f"👤 现有用户数量: {user_count}")
        
        if user_count == 0:
            # 创建默认管理员 - 注意：这里添加了 password 参数
            admin = User(
                username='admin',
                display_name='系统管理员',
                password='admin123',  # 添加密码参数
                email='admin@example.com',
                department='系统管理部',
                is_admin=True
            )
            db.session.add(admin)
            
            # 创建普通用户 - 同样添加 password 参数
            user1 = User(
                username='user1',
                display_name='张三',
                password='user123',  # 添加密码参数
                email='user1@example.com',
                department='工程一部',
                is_admin=False
            )
            db.session.add(user1)
            
            db.session.commit()
            print("✅ 默认用户创建完成")
            print("   管理员: admin / admin123")
            print("   普通用户: user1 / user123")
        else:
            print("⚠️ 用户已存在，跳过创建")
            
        # 检查工作项数据
        workitem_count = WorkItem.query.count()
        print(f"🏗️  工作项数量: {workitem_count}")
        
        if workitem_count == 0:
            print("正在插入示例工作项数据...")
            # 插入示例工作项数据
            sample_items = [
                {'code': 'TJ001', 'name': '开挖', 'labor_coefficient': 0.2, 'unit': 'm3', 'category': '基础开挖'},
                {'code': 'TJ002', 'name': '浇筑', 'labor_coefficient': 1, 'unit': 'm3', 'category': '基础浇筑'},
                {'code': 'TJ003', 'name': '立竿', 'labor_coefficient': 2, 'unit': '个', 'category': '立竿'},
                {'code': 'TJ004', 'name': '安装', 'labor_coefficient': 3, 'unit': '个', 'category': '安装'},
                {'code': 'TJ005', 'name': '调试', 'labor_coefficient': 5, 'unit': '宗', 'category': '调试'},
                {'code': 'TJ006', 'name': '运输', 'labor_coefficient': 0.5, 'unit': '车', 'category': '材料运输'},
                {'code': 'TJ007', 'name': '测量', 'labor_coefficient': 0.8, 'unit': '次', 'category': '工程测量'},
                {'code': 'TJ008', 'name': '砌筑', 'labor_coefficient': 1.5, 'unit': 'm3', 'category': '砌筑工程'},
                {'code': 'TJ009', 'name': '抹灰', 'labor_coefficient': 0.6, 'unit': 'm2', 'category': '抹灰工程'},
                {'code': 'TJ010', 'name': '防水', 'labor_coefficient': 2.5, 'unit': 'm2', 'category': '防水工程'},
            ]
            
            for item_data in sample_items:
                item = WorkItem(**item_data)
                db.session.add(item)
            
            db.session.commit()
            print("✅ 示例工作项数据插入成功！")
        else:
            print("⚠️ 工作项数据已存在，跳过插入")
        
        print("🎉 数据库完全初始化完成！")
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
