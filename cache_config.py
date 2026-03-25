# cache_config.py - 修正版

from flask import request, current_app
import time

def add_cache_headers(response):
    """
    为响应添加缓存控制头部
    """
    # 静态资源缓存策略
    if request.path.startswith('/static/'):
        # 对于静态资源，设置较长的缓存时间
        cache_time = 86400  # 24小时
        
        # 根据文件类型调整缓存时间
        if request.path.endswith(('.css', '.js')):
            # CSS和JS文件缓存1周
            cache_time = 604800
        elif request.path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg')):
            # 图片文件缓存1个月
            cache_time = 2592000
        elif request.path.endswith('.woff2'):
            # 字体文件缓存1年
            cache_time = 31536000
            
        response.headers['Cache-Control'] = f'public, max-age={cache_time}'
        response.headers['Expires'] = time.strftime('%a, %d %b %Y %H:%M:%S GMT', 
                                                   time.gmtime(time.time() + cache_time))
    
    # 动态页面禁止缓存
    elif request.endpoint and not request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    return response
