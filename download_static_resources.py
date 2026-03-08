# download_static_resources.py - 使用Python标准库
import os
import sys
import ssl
import time
import hashlib
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

def create_directories():
    """创建必要的目录结构"""
    directories = [
        'static/vendor/bootstrap/css',
        'static/vendor/bootstrap/js',
        'static/vendor/font-awesome/css',
        'static/vendor/font-awesome/webfonts',
        'static/vendor/jquery'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ 确保目录存在: {directory}")

def download_file(url, filepath, max_retries=3, user_agent=None):
    """使用urllib下载文件"""
    if user_agent is None:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    for attempt in range(max_retries):
        try:
            print(f"正在下载: {url} (尝试 {attempt + 1}/{max_retries})")
            
            # 创建请求对象，设置User-Agent
            req = Request(url, headers={'User-Agent': user_agent})
            
            # 创建SSL上下文，跳过证书验证（仅用于下载公开资源）
            context = ssl._create_unverified_context()
            
            # 下载文件
            with urlopen(req, timeout=30, context=context) as response:
                # 检查响应状态
                if response.status != 200:
                    raise HTTPError(url, response.status, "HTTP错误", response.headers, None)
                
                # 读取数据
                data = response.read()
                
                # 确保目录存在
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                # 保存文件
                with open(filepath, 'wb') as f:
                    f.write(data)
                
                # 计算文件大小
                file_size = len(data) / 1024  # KB
                print(f"✓ 已保存: {filepath} ({file_size:.1f} KB)")
                
                # 验证文件完整性（简单检查）
                if file_size < 1:
                    print(f"⚠ 警告: 文件可能过小，只有 {file_size:.1f} KB")
                
                return True
                
        except HTTPError as e:
            print(f"✗ HTTP错误 {e.code}: {e.reason}")
        except URLError as e:
            print(f"✗ URL错误: {e.reason}")
        except Exception as e:
            print(f"✗ 下载失败: {type(e).__name__}: {e}")
        
        # 如果不是最后一次尝试，等待后重试
        if attempt < max_retries - 1:
            wait_time = (attempt + 1) * 2  # 递增等待时间
            print(f"等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)
    
    print(f"❌ 多次尝试下载失败: {url}")
    return False

def download_bootstrap():
    """下载Bootstrap 5.1.3"""
    print("\n" + "="*60)
    print("下载 Bootstrap 5.1.3")
    print("="*60)
    
    resources = [
        {
            'url': 'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
            'path': 'static/vendor/bootstrap/css/bootstrap.min.css'
        },
        {
            'url': 'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css.map',
            'path': 'static/vendor/bootstrap/css/bootstrap.min.css.map'
        },
        {
            'url': 'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js',
            'path': 'static/vendor/bootstrap/js/bootstrap.bundle.min.js'
        },
        {
            'url': 'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js.map',
            'path': 'static/vendor/bootstrap/js/bootstrap.bundle.min.js.map'
        }
    ]
    
    success_count = 0
    for resource in resources:
        if download_file(resource['url'], resource['path']):
            success_count += 1
    
    print(f"\nBootstrap 下载完成: {success_count}/{len(resources)} 个文件")
    return success_count == len(resources)

def download_fontawesome():
    """下载Font Awesome 6.4.0"""
    print("\n" + "="*60)
    print("下载 Font Awesome 6.4.0")
    print("="*60)
    
    # 下载CSS文件
    css_downloaded = download_file(
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
        'static/vendor/font-awesome/css/all.min.css'
    )
    
    if not css_downloaded:
        print("⚠ Font Awesome CSS下载失败，跳过字体文件")
        return False
    
    print("\n下载关键的Font Awesome字体文件...")
    
    # 只下载最关键的字体文件
    font_files = [
        'fa-solid-900.woff2',
        'fa-brands-400.woff2',
        'fa-regular-400.woff2',
    ]
    
    success_count = 0
    for font in font_files:
        font_url = f'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/{font}'
        font_path = f'static/vendor/font-awesome/webfonts/{font}'
        
        if download_file(font_url, font_path):
            success_count += 1
    
    print(f"\nFont Awesome 字体文件下载: {success_count}/{len(font_files)} 个文件")
    return css_downloaded and success_count > 0

def download_jquery():
    """下载jQuery 3.6.4"""
    print("\n" + "="*60)
    print("下载 jQuery 3.6.4")
    print("="*60)
    
    return download_file(
        'https://code.jquery.com/jquery-3.6.4.min.js',
        'static/vendor/jquery/jquery.min.js'
    )

def fix_font_paths():
    """修复Font Awesome CSS中的字体路径"""
    css_path = 'static/vendor/font-awesome/css/all.min.css'
    
    if not os.path.exists(css_path):
        print(f"✗ 文件不存在: {css_path}")
        return False
    
    try:
        with open(css_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 备份原文件
        backup_path = css_path + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 修复字体路径 - 替换为相对路径
        # Font Awesome 6.4.0的CSS中字体路径是../webfonts/
        content = content.replace('../webfonts/', './webfonts/')
        
        # 保存修复后的文件
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ 已修复Font Awesome字体路径")
        print(f"✓ 原文件已备份到: {backup_path}")
        
        return True
    except Exception as e:
        print(f"✗ 修复字体路径失败: {type(e).__name__}: {e}")
        return False

def create_basic_styles():
    """创建基础的CSS和JS文件"""
    print("\n" + "="*60)
    print("创建基础文件")
    print("="*60)
    
    # 创建基本的CSS文件
    basic_css = """/* 用工申请管理系统 - 基础样式 */
:root {
    --primary-color: #0d6efd;
    --secondary-color: #6c757d;
    --success-color: #198754;
    --danger-color: #dc3545;
    --warning-color: #ffc107;
    --info-color: #0dcaf0;
    --light-color: #f8f9fa;
    --dark-color: #212529;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    line-height: 1.5;
    color: var(--dark-color);
    background-color: var(--light-color);
    margin: 0;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

.container {
    width: 100%;
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 15px;
}

/* 导航栏 */
.navbar {
    background-color: var(--primary-color);
    color: white;
    padding: 1rem 0;
}

.navbar-brand {
    color: white;
    text-decoration: none;
    font-size: 1.25rem;
    font-weight: bold;
}

/* 按钮 */
.btn {
    display: inline-block;
    padding: 0.375rem 0.75rem;
    border: 1px solid transparent;
    border-radius: 0.25rem;
    text-decoration: none;
    cursor: pointer;
    font-size: 1rem;
}

.btn-primary {
    background-color: var(--primary-color);
    color: white;
}

.btn-primary:hover {
    background-color: #0b5ed7;
}

/* 表单 */
.form-control {
    display: block;
    width: 100%;
    padding: 0.375rem 0.75rem;
    border: 1px solid #ced4da;
    border-radius: 0.25rem;
    margin-bottom: 1rem;
}

/* 表格 */
.table {
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0;
}

.table th,
.table td {
    border: 1px solid #dee2e6;
    padding: 0.75rem;
    text-align: left;
}

.table th {
    background-color: #f8f9fa;
}

/* 卡片 */
.card {
    background: white;
    border: 1px solid rgba(0,0,0,.125);
    border-radius: 0.25rem;
    padding: 1.25rem;
    margin: 1rem 0;
}

/* 警告框 */
.alert {
    padding: 1rem;
    border-radius: 0.25rem;
    margin: 1rem 0;
}

.alert-success {
    background-color: #d1e7dd;
    color: #0f5132;
    border: 1px solid #badbcc;
}

.alert-danger {
    background-color: #f8d7da;
    color: #842029;
    border: 1px solid #f5c2c7;
}

.alert-warning {
    background-color: #fff3cd;
    color: #664d03;
    border: 1px solid #ffecb5;
}

/* 页脚 */
.footer {
    background-color: var(--light-color);
    padding: 1.5rem 0;
    margin-top: auto;
    border-top: 1px solid #dee2e6;
    text-align: center;
}

/* 响应式 */
@media (max-width: 768px) {
    .container {
        padding: 0 10px;
    }
}
"""
    
    # 创建CSS文件
    css_dir = 'static/css'
    os.makedirs(css_dir, exist_ok=True)
    
    css_path = os.path.join(css_dir, 'style.css')
    with open(css_path, 'w', encoding='utf-8') as f:
        f.write(basic_css)
    
    print(f"✓ 创建CSS文件: {css_path}")
    
    # 创建基本的JS文件（如果不存在）
    js_dir = 'static/js'
    os.makedirs(js_dir, exist_ok=True)
    
    js_path = os.path.join(js_dir, 'main.js')
    if not os.path.exists(js_path):
        basic_js = """// 用工申请管理系统 - 主JavaScript文件

// 页面加载完成后的初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('页面加载完成');
    
    // 为所有表单添加基本的验证
    var forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            // 简单的必填字段检查
            var requiredFields = form.querySelectorAll('[required]');
            var isValid = true;
            
            requiredFields.forEach(function(field) {
                if (!field.value.trim()) {
                    isValid = false;
                    field.style.borderColor = '#dc3545';
                } else {
                    field.style.borderColor = '';
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                alert('请填写所有必填字段');
            }
        });
    });
    
    // 为下拉菜单添加点击事件（在没有Bootstrap的情况下）
    var dropdowns = document.querySelectorAll('.dropdown-toggle');
    dropdowns.forEach(function(dropdown) {
        dropdown.addEventListener('click', function(e) {
            e.preventDefault();
            var menu = this.nextElementSibling;
            if (menu && menu.classList.contains('dropdown-menu')) {
                menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
            }
        });
    });
    
    // 点击其他地方关闭下拉菜单
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.dropdown')) {
            document.querySelectorAll('.dropdown-menu').forEach(function(menu) {
                menu.style.display = 'none';
            });
        }
    });
});

// 工具函数：显示消息
function showMessage(type, message) {
    var alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-' + type;
    alertDiv.textContent = message;
    
    // 添加到页面顶部
    var container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // 5秒后自动移除
        setTimeout(function() {
            alertDiv.remove();
        }, 5000);
    }
}
"""
        
        with open(js_path, 'w', encoding='utf-8') as f:
            f.write(basic_js)
        
        print(f"✓ 创建JS文件: {js_path}")
    else:
        print(f"✓ JS文件已存在: {js_path}")
    
    return True

def check_resources():
    """检查已下载的资源"""
    print("\n" + "="*60)
    print("检查资源文件")
    print("="*60)
    
    resources_to_check = [
        ('Bootstrap CSS', 'static/vendor/bootstrap/css/bootstrap.min.css', 100),  # 至少100KB
        ('Bootstrap JS', 'static/vendor/bootstrap/js/bootstrap.bundle.min.js', 50),  # 至少50KB
        ('Font Awesome CSS', 'static/vendor/font-awesome/css/all.min.css', 100),  # 至少100KB
        ('jQuery', 'static/vendor/jquery/jquery.min.js', 80),  # 至少80KB
    ]
    
    all_ok = True
    for name, path, min_size_kb in resources_to_check:
        if os.path.exists(path):
            size_kb = os.path.getsize(path) / 1024
            status = "✓" if size_kb >= min_size_kb else "⚠"
            print(f"{status} {name}: {path} ({size_kb:.1f} KB)")
            
            if size_kb < min_size_kb:
                all_ok = False
                print(f"  警告: 文件可能不完整，期望至少 {min_size_kb} KB")
        else:
            print(f"✗ {name}: 文件不存在 {path}")
            all_ok = False
    
    # 检查字体文件
    font_dir = 'static/vendor/font-awesome/webfonts'
    if os.path.exists(font_dir):
        font_files = [f for f in os.listdir(font_dir) if f.endswith(('.woff2', '.ttf'))]
        print(f"✓ Font Awesome 字体文件: {len(font_files)} 个文件")
    else:
        print(f"✗ Font Awesome 字体目录不存在: {font_dir}")
        all_ok = False
    
    return all_ok

def main():
    """主函数"""
    print("开始下载静态资源...")
    print("="*60)
    print("注意: 此脚本使用Python标准库，无需安装额外依赖")
    print("="*60)
    
    # 创建目录
    create_directories()
    
    # 下载资源
    bootstrap_ok = download_bootstrap()
    fontawesome_ok = download_fontawesome()
    jquery_ok = download_jquery()
    
    # 修复字体路径
    if fontawesome_ok:
        fix_font_paths()
    
    # 创建基础文件
    create_basic_styles()
    
    # 检查资源
    resources_ok = check_resources()
    
    print("\n" + "="*60)
    if resources_ok:
        print("✅ 资源下载完成！")
    else:
        print("⚠ 资源下载完成，但部分文件可能有问题")
    
    print("\n下一步:")
    print("1. 确保 templates/base.html 已更新为使用本地资源")
    print("2. 重启Flask应用")
    print("3. 清除浏览器缓存后测试")
    print("="*60)
    
    return resources_ok

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n下载被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生未预期的错误: {type(e).__name__}: {e}")
        sys.exit(1)
