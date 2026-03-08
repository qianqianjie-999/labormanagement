# run.bat - Windows 开发环境启动脚本
@echo off
chcp 65001 >nul
echo ======================================
echo   劳动用工管理系统 - 开发服务器
echo ======================================

cd /d "%~dp0"

REM 检查虚拟环境
if exist ".venv\Scripts\activate.bat" (
    echo ✅ 使用虚拟环境：.venv
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo ✅ 使用虚拟环境：venv
    call venv\Scripts\activate.bat
) else (
    echo ❌ 未找到虚拟环境，请先创建:
    echo    python -m venv venv
    exit /b 1
)

REM 加载环境变量
if exist "config.env" (
    echo ✅ 加载环境配置：config.env
    for /f "delims=" %%a in ('findstr /R /V "^#" config.env ^| findstr /R /V "^$"') do (
        set "%%a"
    )
)

REM 启动服务
echo.
echo 启动开发服务器...
echo 访问地址：http://127.0.0.1:5000
echo.

python manage.py runserver --debug

pause
