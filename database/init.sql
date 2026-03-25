-- 劳动用工管理系统数据库初始化脚本
-- Labor Management System Database Initialization Script

-- ============================================
-- 创建数据库用户和授权
-- ============================================

-- 创建数据库用户（如果不存在）
-- 用户名：labor_app_user
-- 密码：labor_app_password
CREATE USER IF NOT EXISTS 'labor_app_user'@'localhost' IDENTIFIED BY 'labor_app_password';
CREATE USER IF NOT EXISTS 'labor_app_user'@'::1' IDENTIFIED BY 'labor_app_password';
CREATE USER IF NOT EXISTS 'labor_app_user'@'127.0.0.1' IDENTIFIED BY 'labor_app_password';

-- 授予权限
GRANT ALL PRIVILEGES ON labor_application_db.* TO 'labor_app_user'@'localhost';
GRANT ALL PRIVILEGES ON labor_application_db.* TO 'labor_app_user'@'::1';
GRANT ALL PRIVILEGES ON labor_application_db.* TO 'labor_app_user'@'127.0.0.1';

FLUSH PRIVILEGES;

-- ============================================
-- 创建数据库和表
-- ============================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS labor_application_db
DEFAULT CHARACTER SET utf8mb4
DEFAULT COLLATE utf8mb4_unicode_ci;

USE labor_application_db;

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL COMMENT '用户名',
    display_name VARCHAR(100) NOT NULL COMMENT '显示名称',
    password_hash VARCHAR(200) NOT NULL COMMENT '密码哈希',
    email VARCHAR(120) COMMENT '邮箱',
    department VARCHAR(100) COMMENT '部门',
    is_admin BOOLEAN DEFAULT FALSE COMMENT '是否管理员',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    last_login DATETIME COMMENT '最后登录时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- 创建分部分项工程表（用工系数主数据）
CREATE TABLE IF NOT EXISTS work_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL COMMENT '分部分项代码',
    name VARCHAR(100) NOT NULL COMMENT '分部分项名称',
    labor_coefficient FLOAT NOT NULL COMMENT '单位人工系数',
    unit VARCHAR(20) NOT NULL COMMENT '计量单位',
    category VARCHAR(50) NOT NULL COMMENT '所属分类',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分部分项工程表';

-- 创建用工申请表
CREATE TABLE IF NOT EXISTS labor_applications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    department VARCHAR(100) NOT NULL COMMENT '申请部门',
    applicant VARCHAR(50) NOT NULL COMMENT '申请人',
    project_name VARCHAR(200) NOT NULL COMMENT '项目名称',
    project_description TEXT COMMENT '项目说明',
    worker_names TEXT COMMENT '工人名单',
    total_required_labor FLOAT DEFAULT 0.0 COMMENT '系统计算总人工',
    total_user_proposed FLOAT DEFAULT 0.0 COMMENT '用户申请总人工',
    approved_labor FLOAT COMMENT '审批后人工数',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态：pending=待处理，approved=已批准，rejected=已拒绝',
    approved_by VARCHAR(100) COMMENT '审批人',
    approval_comment TEXT COMMENT '审批意见',
    approval_time DATETIME COMMENT '审批时间',
    user_id INT NOT NULL COMMENT '创建用户 ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_status (status),
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用工申请表';

-- 创建申请明细项表（包含快照功能）
CREATE TABLE IF NOT EXISTS application_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT NOT NULL COMMENT '用工申请 ID',
    work_item_id INT NOT NULL COMMENT '分部分项工程 ID',
    quantity FLOAT NOT NULL COMMENT '工程量',
    required_labor FLOAT NOT NULL COMMENT '系统计算人工',
    user_proposed_labor FLOAT COMMENT '用户申请人工',
    snapshot_code VARCHAR(20) COMMENT '快照 - 代码',
    snapshot_name VARCHAR(100) COMMENT '快照 - 名称',
    snapshot_labor_coefficient FLOAT COMMENT '快照 - 人工系数',
    snapshot_unit VARCHAR(20) COMMENT '快照 - 单位',
    snapshot_category VARCHAR(50) COMMENT '快照 - 分类',
    FOREIGN KEY (application_id) REFERENCES labor_applications(id) ON DELETE CASCADE,
    FOREIGN KEY (work_item_id) REFERENCES work_items(id) ON DELETE RESTRICT,
    INDEX idx_application_id (application_id),
    INDEX idx_work_item_id (work_item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='申请明细项表';

-- ============================================
-- 初始化数据 - 示例工作项
-- ============================================

-- 插入示例分部分项工程数据
INSERT INTO work_items (code, name, labor_coefficient, unit, category) VALUES
('TJ001', '开挖', 0.2, 'm3', '基础开挖'),
('TJ002', '浇筑', 1.0, 'm3', '基础浇筑'),
('TJ003', '立竿', 2.0, '个', '立竿'),
('TJ004', '安装', 3.0, '个', '安装'),
('TJ005', '调试', 5.0, '宗', '调试'),
('TJ006', '运输', 0.5, '车', '材料运输'),
('TJ007', '测量', 0.8, '次', '工程测量'),
('TJ008', '砌筑', 1.5, 'm3', '砌筑工程'),
('TJ009', '抹灰', 0.6, 'm2', '抹灰工程'),
('TJ010', '防水', 2.5, 'm2', '防水工程')
ON DUPLICATE KEY UPDATE code=code;

-- ============================================
-- 说明
-- ============================================
-- 默认用户需要通过 init_tables.py 创建
-- 运行：python init_tables.py
--
-- 默认账号:
--   管理员：admin / admin123
--   普通用户：user1 / user123
-- ============================================
