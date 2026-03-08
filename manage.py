#!/usr/bin/env python3
"""
manage.py - 项目管理脚本

用法:
    python manage.py runserver         # 启动开发服务器
    python manage.py shell             # 进入 Python shell
    python manage.py init-db           # 初始化数据库
    python manage.py create-user       # 创建用户
    python manage.py list-users        # 列出所有用户
"""

import os
import sys
import click
from getpass import getpass

from app import create_app, db
from models import User, WorkItem, LaborApplication

app = create_app()


@app.cli.command("runserver")
@click.option('--host', default='127.0.0.1', help='服务器主机地址')
@click.option('--port', default=5000, help='服务器端口')
@click.option('--debug', is_flag=True, help='启用调试模式')
def runserver(host, port, debug):
    """启动开发服务器"""
    app.run(host=host, port=port, debug=debug)


@app.cli.command("shell")
def shell():
    """进入 Python shell"""
    import code
    from models import db, User, WorkItem, LaborApplication, ApplicationItem

    context = {
        'app': app,
        'db': db,
        'User': User,
        'WorkItem': WorkItem,
        'LaborApplication': LaborApplication,
        'ApplicationItem': ApplicationItem
    }

    try:
        import IPython
        IPython.embed(colors="neutral")
    except ImportError:
        code.interact(local=context)


@app.cli.command("init-db")
@click.option('--drop', is_flag=True, help='先删除现有表')
@click.option('--yes', is_flag=True, help='确认执行，不提示')
def init_db(drop, yes):
    """初始化数据库表"""
    if drop:
        if not yes:
            click.confirm('确定要删除所有表吗？此操作不可逆！', abort=True)
        with app.app_context():
            db.drop_all()
            click.echo("✅ 已删除所有表")

    with app.app_context():
        db.create_all()
        click.echo("✅ 数据库表创建成功")

        # 检查是否已有用户
        user_count = User.query.count()
        if user_count == 0:
            click.echo("正在创建默认用户...")
            admin = User(
                username='admin',
                display_name='系统管理员',
                password='admin123',
                email='admin@example.com',
                department='系统管理部',
                is_admin=True
            )
            db.session.add(admin)

            user1 = User(
                username='user1',
                display_name='张三',
                password='user123',
                email='user1@example.com',
                department='工程一部',
                is_admin=False
            )
            db.session.add(user1)
            db.session.commit()
            click.echo("✅ 默认用户创建完成")
            click.echo("   管理员：admin / admin123")
            click.echo("   普通用户：user1 / user123")

        # 检查工作项
        workitem_count = WorkItem.query.count()
        if workitem_count == 0:
            click.echo("正在插入示例工作项...")
            sample_items = [
                {'code': 'TJ001', 'name': '开挖', 'labor_coefficient': 0.2, 'unit': 'm³', 'category': '基础开挖'},
                {'code': 'TJ002', 'name': '浇筑', 'labor_coefficient': 1, 'unit': 'm³', 'category': '基础浇筑'},
                {'code': 'TJ003', 'name': '立竿', 'labor_coefficient': 2, 'unit': '个', 'category': '立竿'},
                {'code': 'TJ004', 'name': '安装', 'labor_coefficient': 3, 'unit': '个', 'category': '安装'},
                {'code': 'TJ005', 'name': '调试', 'labor_coefficient': 5, 'unit': '宗', 'category': '调试'},
                {'code': 'TJ006', 'name': '运输', 'labor_coefficient': 0.5, 'unit': '车', 'category': '材料运输'},
                {'code': 'TJ007', 'name': '测量', 'labor_coefficient': 0.8, 'unit': '次', 'category': '工程测量'},
                {'code': 'TJ008', 'name': '砌筑', 'labor_coefficient': 1.5, 'unit': 'm³', 'category': '砌筑工程'},
                {'code': 'TJ009', 'name': '抹灰', 'labor_coefficient': 0.6, 'unit': 'm²', 'category': '抹灰工程'},
                {'code': 'TJ010', 'name': '防水', 'labor_coefficient': 2.5, 'unit': 'm²', 'category': '防水工程'},
            ]
            for item_data in sample_items:
                item = WorkItem(**item_data)
                db.session.add(item)
            db.session.commit()
            click.echo("✅ 示例工作项插入完成")


@app.cli.command("create-user")
@click.option('--username', prompt='用户名', help='登录用户名')
@click.option('--display-name', prompt='显示名称', help='用户显示名称')
@click.option('--email', prompt='邮箱', help='用户邮箱')
@click.option('--department', prompt='部门', help='所属部门')
@click.option('--is-admin', is_flag=True, help='是否为管理员')
@click.option('--password', prompt='密码', hide_input=True, confirmation_prompt=True, help='登录密码')
def create_user(username, display_name, email, department, is_admin, password):
    """创建新用户"""
    with app.app_context():
        # 检查用户名是否已存在
        existing = User.query.filter_by(username=username).first()
        if existing:
            click.echo(f"❌ 用户名 '{username}' 已存在")
            return

        user = User(
            username=username,
            display_name=display_name,
            password=password,
            email=email,
            department=department,
            is_admin=is_admin
        )
        db.session.add(user)
        db.session.commit()
        click.echo(f"✅ 用户 '{username}' 创建成功")


@app.cli.command("list-users")
def list_users():
    """列出所有用户"""
    with app.app_context():
        users = User.query.all()
        if not users:
            click.echo("暂无用户")
            return

        click.echo("\n{:<15} {:<20} {:<25} {:<15} {:<10}".format(
            '用户名', '显示名称', '邮箱', '部门', '角色'))
        click.echo("-" * 85)
        for user in users:
            role = '管理员' if user.is_admin else '普通用户'
            click.echo("{:<15} {:<20} {:<25} {:<15} {:<10}".format(
                user.username, user.display_name, user.email or '-',
                user.department or '-', role))
        click.echo("-" * 85)
        click.echo(f"共 {len(users)} 个用户")


@app.cli.command("delete-user")
@click.argument('username')
@click.option('--yes', is_flag=True, help='确认执行，不提示')
def delete_user(username, yes):
    """删除用户"""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            click.echo(f"❌ 用户 '{username}' 不存在")
            return

        if not yes:
            click.confirm(f"确定要删除用户 '{username}' 吗？", abort=True)

        db.session.delete(user)
        db.session.commit()
        click.echo(f"✅ 用户 '{username}' 已删除")


@app.cli.command("update-coefficient")
@click.argument('code')
@click.option('--coefficient', type=float, prompt='输入新的用工系数')
def update_coefficient(code, coefficient):
    """更新工作项用工系数"""
    with app.app_context():
        work_item = WorkItem.query.filter_by(code=code).first()
        if not work_item:
            click.echo(f"❌ 工作项 '{code}' 不存在")
            return

        old_coefficient = work_item.labor_coefficient
        work_item.labor_coefficient = coefficient
        db.session.commit()
        click.echo(f"✅ 工作项 '{code}' 的系数已从 {old_coefficient} 更新为 {coefficient}")


if __name__ == '__main__':
    app.cli()
