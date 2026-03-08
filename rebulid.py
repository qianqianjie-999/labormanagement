# rebuild_database.py - 一键重建数据库（修复版）

from app import create_app
from models import db, User, WorkItem
import os


def create_directories():
    """创建必要的目录"""
    directories = ['uploads', 'exports', 'logs', 'static/fonts']

    for directory in directories:
        path = os.path.join(os.path.dirname(__file__), directory)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            print(f"创建目录: {directory}")


def rebuild_database():
    """一键重建数据库（删除所有数据，重新创建）"""
    print("=== 一键重建数据库 ===")
    print("警告：这将删除所有现有数据！")

    confirm = input("确定要继续吗？输入 'yes' 继续: ")
    if confirm.lower() != 'yes':
        print("操作已取消")
        return

    # 创建必要目录
    create_directories()

    # 创建应用实例
    app = create_app()

    with app.app_context():
        try:
            print("正在连接数据库...")

            # 1. 删除所有表
            print("删除所有表...")
            db.drop_all()

            # 2. 重新创建所有表（包含快照字段）
            print("重新创建所有表...")
            db.create_all()

            # 3. 创建默认管理员
            print("创建默认用户...")
            admin = User(
                username='admin',
                display_name='系统管理员',
                password='admin123',
                email='admin@example.com',
                department='管理部',
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

            db.session.add(admin)
            db.session.add(user1)
            db.session.commit()
            print("✓ 默认用户创建成功")

            # 4. 添加示例分部分项
            print("添加示例分部分项...")
            items = [
                {'code': 'QT001', 'name': '其它', 'labor_coefficient': 1, 'unit': '工', 'category': '无定额用工'},
            ]

            for data in items:
                item = WorkItem(**data)
                db.session.add(item)

            db.session.commit()
            print("✓ 示例数据插入成功")

            # 统计信息
            user_count = User.query.count()
            item_count = WorkItem.query.count()

            print("\n" + "=" * 50)
            print("数据库重建完成！")
            print("=" * 50)
            print(f"用户数量: {user_count}")
            print(f"分部分项工程数量: {item_count}")
            print("\n登录信息:")
            print("管理员账号: admin / admin123")
            print("普通用户账号: user1 / user123")
            print("\n访问地址: http://localhost:5000/login")
            print("=" * 50)

        except Exception as e:
            db.session.rollback()
            print(f"错误：{str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    rebuild_database()
