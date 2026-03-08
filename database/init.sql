-- =====================================================
-- 劳动用工管理系统 - 数据库初始化脚本
-- 适用：MySQL 5.7+ / MariaDB 10.3+
-- =====================================================

-- 设置字符集
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- =====================================================
-- 1. 创建数据库
-- =====================================================
CREATE DATABASE IF NOT EXISTS `labor_application_db`
DEFAULT CHARACTER SET utf8mb4
DEFAULT COLLATE utf8mb4_unicode_ci;

USE `labor_application_db`;

-- =====================================================
-- 2. 创建数据库用户并授权
-- =====================================================
-- 为 IPv4 连接创建用户
DROP USER IF EXISTS 'labor_app_user'@'127.0.0.1';
CREATE USER 'labor_app_user'@'127.0.0.1' IDENTIFIED BY 'labor_app_password';

-- 为 IPv6 连接创建用户（防止::1 连接问题）
DROP USER IF EXISTS 'labor_app_user'@'::1';
CREATE USER 'labor_app_user'@'::1' IDENTIFIED BY 'labor_app_password';

-- 为本地连接创建用户
DROP USER IF EXISTS 'labor_app_user'@'localhost';
CREATE USER 'labor_app_user'@'localhost' IDENTIFIED BY 'labor_app_password';

-- 授权
GRANT ALL PRIVILEGES ON `labor_application_db`.* TO 'labor_app_user'@'127.0.0.1';
GRANT ALL PRIVILEGES ON `labor_application_db`.* TO 'labor_app_user'@'::1';
GRANT ALL PRIVILEGES ON `labor_application_db`.* TO 'labor_app_user'@'localhost';

FLUSH PRIVILEGES;

-- =====================================================
-- 3. 创建表结构
-- =====================================================

-- -----------------------------------------------------
-- 3.1 用户表
-- -----------------------------------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `display_name` VARCHAR(100) NOT NULL,
    `password_hash` VARCHAR(200) NOT NULL,
    `email` VARCHAR(120),
    `department` VARCHAR(100),
    `is_admin` TINYINT(1) DEFAULT 0,
    `is_active` TINYINT(1) DEFAULT 1,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `last_login` DATETIME,
    PRIMARY KEY (`id`),
    INDEX `idx_username` (`username`),
    INDEX `idx_department` (`department`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='用户表';

-- -----------------------------------------------------
-- 3.2 工作项表
-- -----------------------------------------------------
DROP TABLE IF EXISTS `work_items`;
CREATE TABLE `work_items` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `code` VARCHAR(20) NOT NULL UNIQUE,
    `name` VARCHAR(100) NOT NULL,
    `labor_coefficient` DECIMAL(10,4) NOT NULL,
    `unit` VARCHAR(20) NOT NULL,
    `category` VARCHAR(50) NOT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_code` (`code`),
    INDEX `idx_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='工作项表';

-- -----------------------------------------------------
-- 3.3 用工申请表
-- -----------------------------------------------------
DROP TABLE IF EXISTS `labor_applications`;
CREATE TABLE `labor_applications` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `department` VARCHAR(100) NOT NULL,
    `applicant` VARCHAR(50) NOT NULL,
    `project_name` VARCHAR(200) NOT NULL,
    `project_description` TEXT,
    `worker_names` TEXT,
    `total_required_labor` DECIMAL(10,2) DEFAULT 0.00,
    `total_user_proposed` DECIMAL(10,2) DEFAULT 0.00,
    `approved_labor` DECIMAL(10,2),
    `status` VARCHAR(20) DEFAULT 'pending',
    `approved_by` VARCHAR(100),
    `approval_comment` TEXT,
    `approval_time` DATETIME,
    `user_id` INT NOT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_department` (`department`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_created_at` (`created_at`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='用工申请表';

-- -----------------------------------------------------
-- 3.4 申请明细表
-- -----------------------------------------------------
DROP TABLE IF EXISTS `application_items`;
CREATE TABLE `application_items` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `application_id` INT NOT NULL,
    `work_item_id` INT NOT NULL,
    `quantity` DECIMAL(10,2) NOT NULL,
    `required_labor` DECIMAL(10,2) NOT NULL,
    `user_proposed_labor` DECIMAL(10,2),
    `snapshot_code` VARCHAR(20),
    `snapshot_name` VARCHAR(100),
    `snapshot_labor_coefficient` DECIMAL(10,4),
    `snapshot_unit` VARCHAR(20),
    `snapshot_category` VARCHAR(50),
    PRIMARY KEY (`id`),
    INDEX `idx_application_id` (`application_id`),
    INDEX `idx_work_item_id` (`work_item_id`),
    FOREIGN KEY (`application_id`) REFERENCES `labor_applications`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`work_item_id`) REFERENCES `work_items`(`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='申请明细表';

-- =====================================================
-- 4. 插入初始数据
-- =====================================================

-- -----------------------------------------------------
-- 4.1 插入默认用户
-- -----------------------------------------------------
-- 默认管理员：admin / admin123
INSERT INTO `users` (`username`, `display_name`, `password_hash`, `email`, `department`, `is_admin`, `is_active`)
VALUES (
    'admin',
    '系统管理员',
    'scrypt:32768:8:1$[salt]$[hash]',  -- 占位符，实际密码由应用生成
    'admin@example.com',
    '系统管理部',
    1,
    1
);

-- 默认普通用户：user1 / user123
INSERT INTO `users` (`username`, `display_name`, `password_hash`, `email`, `department`, `is_admin`, `is_active`)
VALUES (
    'user1',
    '张三',
    'scrypt:32768:8:1$[salt]$[hash]',  -- 占位符，实际密码由应用生成
    'user1@example.com',
    '工程一部',
    0,
    1
);

-- -----------------------------------------------------
-- 4.2 插入示例工作项
-- -----------------------------------------------------
INSERT INTO `work_items` (`code`, `name`, `labor_coefficient`, `unit`, `category`) VALUES
('TJ001', '开挖', 0.2000, 'm³', '基础开挖'),
('TJ002', '浇筑', 1.0000, 'm³', '基础浇筑'),
('TJ003', '立竿', 2.0000, '个', '立竿'),
('TJ004', '安装', 3.0000, '个', '安装'),
('TJ005', '调试', 5.0000, '宗', '调试'),
('TJ006', '运输', 0.5000, '车', '材料运输'),
('TJ007', '测量', 0.8000, '次', '工程测量'),
('TJ008', '砌筑', 1.5000, 'm³', '砌筑工程'),
('TJ009', '抹灰', 0.6000, 'm²', '抹灰工程'),
('TJ010', '防水', 2.5000, 'm²', '防水工程'),
('TJ011', '钢筋制作', 1.2000, '吨', '钢筋工程'),
('TJ012', '模板安装', 0.9000, 'm²', '模板工程'),
('TJ013', '混凝土养护', 0.3000, 'm³', '养护工程'),
('TJ014', '场地清理', 0.1500, 'm²', '清理工程'),
('TJ015', '设备搬运', 0.7000, '台', '设备工程');

-- =====================================================
-- 5. 创建视图（可选）
-- =====================================================

-- 申请详情视图
DROP VIEW IF EXISTS `v_application_details`;
CREATE VIEW `v_application_details` AS
SELECT
    a.id AS application_id,
    a.department,
    a.applicant,
    a.project_name,
    a.status,
    a.total_required_labor,
    a.total_user_proposed,
    a.approved_labor,
    a.created_at,
    u.display_name AS creator_name,
    COUNT(i.id) AS item_count
FROM labor_applications a
LEFT JOIN users u ON a.user_id = u.id
LEFT JOIN application_items i ON a.id = i.application_id
GROUP BY a.id, a.department, a.applicant, a.project_name, a.status,
         a.total_required_labor, a.total_user_proposed, a.approved_labor,
         a.created_at, u.display_name;

-- =====================================================
-- 6. 创建存储过程（可选）
-- =====================================================

-- 更新申请状态
DELIMITER //
DROP PROCEDURE IF EXISTS `sp_update_application_status`//
CREATE PROCEDURE `sp_update_application_status`(
    IN p_application_id INT,
    IN p_status VARCHAR(20),
    IN p_approved_by VARCHAR(100),
    IN p_approval_comment TEXT,
    IN p_approved_labor DECIMAL(10,2)
)
BEGIN
    UPDATE labor_applications
    SET status = p_status,
        approved_by = p_approved_by,
        approval_comment = p_approval_comment,
        approved_labor = p_approved_labor,
        approval_time = NOW()
    WHERE id = p_application_id;
END//
DELIMITER ;

-- =====================================================
-- 7. 完成提示
-- =====================================================
SELECT '✅ 数据库初始化完成！' AS status;
SELECT '数据库：labor_application_db' AS database_name;
SELECT '用户：labor_app_user' AS db_user;
SELECT '请修改密码以确保安全！' AS reminder;

SET FOREIGN_KEY_CHECKS = 1;
