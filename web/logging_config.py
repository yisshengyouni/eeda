# -*- coding: UTF-8 -*-
"""
日志配置示例

使用方式:
    from web.logging_config import setup_logging
    setup_logging(level='INFO', log_file='tts_api.log')
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
import os


def setup_logging(
    level='INFO',
    log_file=None,
    max_bytes=10*1024*1024,  # 10MB
    backup_count=5,
    log_format=None
):
    """
    配置日志系统
    
    参数:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径，如果为 None 则只输出到控制台
        max_bytes: 单个日志文件最大大小（默认 10MB）
        backup_count: 保留的日志文件数量（默认 5 个）
        log_format: 日志格式字符串
    """
    
    if log_format is None:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 获取日志级别
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # 清除已有的 handlers（避免重复）
    root_logger.handlers.clear()
    
    # 创建格式化器
    formatter = logging.Formatter(log_format)
    
    # 添加控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 如果指定了日志文件，添加文件 handler
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # 添加轮转文件 handler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        logging.info(f"日志文件: {log_file} (最大 {max_bytes} bytes, 保留 {backup_count} 个)")
    
    logging.info(f"日志级别: {level}")
    logging.info(f"日志配置完成")


def setup_flask_logging(app, level='INFO', log_file=None):
    """
    为 Flask 应用配置日志
    
    参数:
        app: Flask 应用实例
        level: 日志级别
        log_file: 日志文件路径
    """
    setup_logging(level=level, log_file=log_file)
    
    # 设置 Flask 的日志级别
    app.logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 将 Flask 的日志也输出到相同的 handlers
    for handler in logging.getLogger().handlers:
        app.logger.addHandler(handler)
    
    app.logger.info("Flask 应用日志配置完成")


# 常用日志配置预设
class LoggingPresets:
    """日志配置预设"""
    
    @staticmethod
    def development():
        """开发环境配置 - DEBUG 级别，输出到控制台"""
        setup_logging(level='DEBUG')
    
    @staticmethod
    def production(log_file='logs/tts_api.log'):
        """生产环境配置 - INFO 级别，输出到文件和控制台"""
        setup_logging(
            level='INFO',
            log_file=log_file,
            max_bytes=50*1024*1024,  # 50MB
            backup_count=10
        )
    
    @staticmethod
    def debug_with_file(log_file='logs/tts_debug.log'):
        """调试配置 - DEBUG 级别，输出到文件"""
        setup_logging(
            level='DEBUG',
            log_file=log_file,
            max_bytes=100*1024*1024,  # 100MB
            backup_count=20
        )
    
    @staticmethod
    def minimal():
        """最小配置 - 只输出 WARNING 及以上"""
        setup_logging(level='WARNING')


# 使用示例
if __name__ == '__main__':
    # 示例 1: 开发环境
    print("示例 1: 开发环境日志配置")
    LoggingPresets.development()
    logging.debug("这是一条 DEBUG 日志")
    logging.info("这是一条 INFO 日志")
    logging.warning("这是一条 WARNING 日志")
    logging.error("这是一条 ERROR 日志")
    
    print("\n" + "="*60 + "\n")
    
    # 示例 2: 生产环境
    print("示例 2: 生产环境日志配置")
    LoggingPresets.production('logs/example.log')
    logging.info("生产环境日志测试")
