# -*- coding: UTF-8 -*-
"""
日志配置 - 控制台输出

使用方式:
    from web.logging_config import setup_logging
    setup_logging(level='INFO')
"""

import logging
import sys


def setup_logging(
    level='INFO',
    log_format=None
):
    """
    配置日志系统（仅控制台输出）
    
    参数:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
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
    
    logging.info(f"日志级别: {level} (控制台输出)")
    logging.info(f"日志配置完成")


def setup_flask_logging(app, level='INFO'):
    """
    为 Flask 应用配置日志（仅控制台输出）
    
    参数:
        app: Flask 应用实例
        level: 日志级别
    """
    setup_logging(level=level)
    
    # 设置 Flask 的日志级别
    app.logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 将 Flask 的日志也输出到相同的 handlers
    for handler in logging.getLogger().handlers:
        app.logger.addHandler(handler)
    
    app.logger.info("Flask 应用日志配置完成 (控制台输出)")


# 常用日志配置预设
class LoggingPresets:
    """日志配置预设（仅控制台输出）"""
    
    @staticmethod
    def development():
        """开发环境配置 - DEBUG 级别，输出到控制台"""
        setup_logging(level='DEBUG')
    
    @staticmethod
    def production():
        """生产环境配置 - INFO 级别，输出到控制台"""
        setup_logging(level='INFO')
    
    @staticmethod
    def debug():
        """调试配置 - DEBUG 级别，输出到控制台"""
        setup_logging(level='DEBUG')
    
    @staticmethod
    def minimal():
        """最小配置 - 只输出 WARNING 及以上"""
        setup_logging(level='WARNING')


# 使用示例
if __name__ == '__main__':
    # 示例 1: 开发环境
    print("示例 1: 开发环境日志配置 (DEBUG)")
    print("=" * 60)
    LoggingPresets.development()
    logging.debug("这是一条 DEBUG 日志")
    logging.info("这是一条 INFO 日志")
    logging.warning("这是一条 WARNING 日志")
    logging.error("这是一条 ERROR 日志")
    
    print("\n" + "="*60 + "\n")
    
    # 示例 2: 生产环境
    print("示例 2: 生产环境日志配置 (INFO)")
    print("=" * 60)
    LoggingPresets.production()
    logging.info("生产环境日志测试")
    logging.warning("这是一条 WARNING 日志")
