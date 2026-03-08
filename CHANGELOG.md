# 更新日志

所有重要的项目变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

### 新增
- 项目管理脚本 `manage.py`，支持以下命令：
  - `runserver` - 启动开发服务器
  - `init-db` - 初始化数据库
  - `create-user` - 创建用户
  - `list-users` - 列出所有用户
  - `delete-user` - 删除用户
  - `update-coefficient` - 更新工作项系数
- 日志配置模块 `logging_config.py`
- 开发环境启动脚本 `run.sh` (Linux/Mac) 和 `run.bat` (Windows)
- 配置文件示例 `config.env.example`
- Apache 配置示例 `apache.conf.example`
- 更新日志 `CHANGELOG.md`

### 优化
- 优化 `config.py`，支持环境变量配置
- 优化数据库连接 URI，默认使用 `127.0.0.1` 避免 IPv6 问题
- 优化 `.gitignore`，添加更多忽略规则
- 新增多环境配置（开发、生产、测试）

### 文档
- 完善 `README.md`，添加更多使用说明
- 完善 `DEPLOYMENT.md`，添加详细的部署步骤

---

## [1.0.0] - 2024-01-01

### 新增
- 初始版本发布
- 用户管理功能
- 用工申请功能
- 审批流程功能
- 工作项管理
- PDF 导出功能
- Excel 导入功能
