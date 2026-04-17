# -*- coding: UTF-8 -*-
"""
Flask 应用示例 - 展示如何集成 TTS API 和日志配置

运行方式:
    python web/app_example.py
"""

from flask import Flask, request
import logging

# 导入日志配置
from web.logging_config import setup_flask_logging, LoggingPresets

# 导入 TTS 路由
from web.tts_api import register_tts_routes


def create_app(config_name='development'):
    """
    创建 Flask 应用工厂函数
    
    参数:
        config_name: 配置名称 (development, production, debug)
    """
    app = Flask(__name__)
    
    # 根据配置名称选择日志预设
    if config_name == 'production':
        LoggingPresets.production('logs/tts_api.log')
    elif config_name == 'debug':
        LoggingPresets.debug_with_file('logs/tts_debug.log')
    else:
        LoggingPresets.development()
    
    # 配置 Flask 日志
    setup_flask_logging(app, level='DEBUG')
    
    app.logger.info("=" * 60)
    app.logger.info("🚀 Flask 应用启动")
    app.logger.info(f"📝 配置环境: {config_name}")
    
    # 注册 TTS 路由
    register_tts_routes(app)
    app.logger.info("✅ TTS 路由注册完成")
    
    # 添加健康检查端点
    @app.route('/health', methods=['GET'])
    def health_check():
        """健康检查"""
        app.logger.debug("收到健康检查请求")
        return {
            'status': 'healthy',
            'service': 'TTS API',
            'version': '1.0.0'
        }
    
    # 添加请求日志中间件
    @app.before_request
    def log_request():
        """记录每个请求"""
        app.logger.info(f"📨 {request.method} {request.path}")
    
    @app.after_request
    def log_response(response):
        """记录每个响应"""
        app.logger.info(f"📤 响应状态码: {response.status_code}")
        return response
    
    app.logger.info("=" * 60)
    
    return app


if __name__ == '__main__':
    # 创建应用
    app = create_app('development')
    
    # 打印可用路由
    app.logger.info("📋 注册的路由:")
    for rule in app.url_map.iter_rules():
        app.logger.info(f"  {rule.methods} {rule.rule}")
    
    # 启动应用
    app.logger.info("🌐 服务器启动在 http://localhost:5000")
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=False  # 避免重复初始化日志
    )
