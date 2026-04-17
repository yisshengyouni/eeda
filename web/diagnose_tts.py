# -*- coding: UTF-8 -*-
"""
Edge TTS 403 错误诊断和修复脚本

常见问题:
1. edge-tts 版本过旧
2. 服务器 IP 被限制
3. 请求频率过高
4. 网络连接问题

使用方法:
    python web/diagnose_tts.py
"""

import sys
import asyncio
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_edge_tts_version():
    """检查 edge-tts 版本"""
    try:
        import edge_tts
        version = edge_tts.__version__
        logger.info(f"✅ edge-tts 已安装，版本: {version}")
        
        # 检查版本是否过旧
        version_parts = version.split('.')
        major = int(version_parts[0])
        minor = int(version_parts[1])
        
        if major < 7 or (major == 7 and minor < 0):
            logger.warning("⚠️  edge-tts 版本过旧，建议升级到 7.0.2 或更高版本")
            logger.warning("   运行: pip install --upgrade edge-tts")
            return False
        else:
            logger.info("✅ edge-tts 版本符合要求")
            return True
    except ImportError:
        logger.error("❌ edge-tts 未安装")
        logger.error("   运行: pip install edge-tts")
        return False
    except Exception as e:
        logger.error(f"❌ 检查版本时出错: {e}")
        return False


def check_network_connectivity():
    """检查网络连接"""
    logger.info("检查网络连接...")
    
    try:
        import requests
        # 测试基本网络连接
        response = requests.get('https://speech.platform.bing.com', timeout=10)
        logger.info(f"✅ 可以访问 Edge TTS 服务 (状态码: {response.status_code})")
        return True
    except requests.exceptions.Timeout:
        logger.error("❌ 连接超时，请检查网络配置")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("❌ 无法连接到 Edge TTS 服务")
        logger.error("   可能原因:")
        logger.error("   1. 服务器防火墙阻止了连接")
        logger.error("   2. 需要使用代理")
        logger.error("   3. 地区限制")
        return False
    except Exception as e:
        logger.error(f"❌ 网络连接检查失败: {e}")
        return False


async def test_tts_generation():
    """测试 TTS 生成"""
    logger.info("测试 TTS 生成...")
    
    try:
        import edge_tts
        import tempfile
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            output_path = tmp.name
        
        # 尝试生成简短的 TTS
        text = "测试"
        voice = "zh-CN-XiaoxiaoNeural"
        
        logger.info(f"正在生成 TTS: '{text}' (voice: {voice})")
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        
        # 检查文件是否生成成功
        if Path(output_path).exists():
            file_size = Path(output_path).stat().st_size
            logger.info(f"✅ TTS 生成成功，文件大小: {file_size} bytes")
            
            # 清理临时文件
            Path(output_path).unlink()
            return True
        else:
            logger.error("❌ TTS 文件生成失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ TTS 生成测试失败: {e}")
        
        # 提供具体的错误建议
        error_msg = str(e).lower()
        if "403" in error_msg:
            logger.error("")
            logger.error("📋 403 错误解决方案:")
            logger.error("   1. 升级 edge-tts: pip install --upgrade edge-tts")
            logger.error("   2. 检查服务器 IP 是否被限制")
            logger.error("   3. 降低请求频率，添加重试机制")
            logger.error("   4. 考虑使用代理服务器")
            logger.error("   5. 检查是否触发了速率限制")
        elif "timeout" in error_msg or "connection" in error_msg:
            logger.error("")
            logger.error("📋 网络连接问题解决方案:")
            logger.error("   1. 检查服务器防火墙设置")
            logger.error("   2. 配置代理: export HTTPS_PROXY=http://your-proxy:port")
            logger.error("   3. 检查 DNS 解析是否正常")
        elif "rate" in error_msg or "limit" in error_msg:
            logger.error("")
            logger.error("📋 速率限制解决方案:")
            logger.error("   1. 降低请求频率")
            logger.error("   2. 添加请求间隔 (建议 2-3 秒)")
            logger.error("   3. 使用队列控制并发")
        
        return False


def check_ffmpeg():
    """检查 ffmpeg 是否安装"""
    import shutil
    
    if shutil.which('ffmpeg'):
        logger.info("✅ ffmpeg 已安装")
        return True
    else:
        logger.warning("⚠️  ffmpeg 未安装 (仅影响音频合并功能)")
        logger.warning("   macOS: brew install ffmpeg")
        logger.warning("   Ubuntu: sudo apt-get install ffmpeg")
        logger.warning("   CentOS: sudo yum install ffmpeg")
        return False


def print_summary(results):
    """打印诊断总结"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("诊断总结:")
    logger.info("=" * 60)
    
    all_passed = all(results.values())
    
    for check_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        logger.info(f"  {check_name}: {status}")
    
    logger.info("")
    if all_passed:
        logger.info("✅ 所有检查通过！如果仍有问题，请查看应用日志。")
    else:
        logger.info("⚠️  部分检查未通过，请按照上述建议进行修复。")
    
    logger.info("")
    logger.info("推荐的修复步骤:")
    logger.info("  1. 升级 edge-tts: pip install --upgrade edge-tts")
    logger.info("  2. 重启应用服务")
    logger.info("  3. 检查应用日志获取更详细的错误信息")
    logger.info("")


def main():
    """主函数"""
    logger.info("Edge TTS 诊断工具")
    logger.info("=" * 60)
    logger.info("")
    
    results = {}
    
    # 1. 检查 edge-tts 版本
    results["edge-tts 版本"] = check_edge_tts_version()
    logger.info("")
    
    # 2. 检查 ffmpeg
    results["ffmpeg"] = check_ffmpeg()
    logger.info("")
    
    # 3. 检查网络连接
    results["网络连接"] = check_network_connectivity()
    logger.info("")
    
    # 4. 测试 TTS 生成
    try:
        loop = asyncio.get_event_loop()
        results["TTS 生成"] = loop.run_until_complete(test_tts_generation())
    except RuntimeError:
        # Python 3.10+ 可能需要新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results["TTS 生成"] = loop.run_until_complete(test_tts_generation())
        loop.close()
    
    logger.info("")
    
    # 打印总结
    print_summary(results)


if __name__ == '__main__':
    main()
