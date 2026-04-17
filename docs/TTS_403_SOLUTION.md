# Edge TTS 403 错误解决方案

## 问题描述

线上环境出现以下错误：
```
403, message='Invalid response status', 
url=URL('wss://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1?...')
```

## 根本原因

Edge TTS 服务返回 403 错误通常由以下原因导致：

### 1. **IP 地址限制**
- 微软对数据中心 IP 段有限制
- 云服务器（AWS、阿里云、腾讯云等）的 IP 可能被识别为非用户 IP
- 某些地区的 IP 被限制访问

### 2. **请求频率过高（Rate Limiting）**
- 短时间内发送过多请求
- Edge TTS 没有公开的 API 限制文档，但实测约 20-30 请求/分钟
- 并发请求更容易触发限制

### 3. **edge-tts 版本过旧**
- 旧版本使用的 Token 可能已失效
- 微软更新了认证机制

### 4. **网络环境问题**
- 防火墙拦截 WebSocket 连接
- 代理配置问题
- DNS 解析异常

## ✅ 已实施的解决方案

### 1. 添加自动重试机制

已在 `tts_api.py` 中添加：
- 最多重试 3 次
- 递增延迟（2秒、4秒、6秒）
- 详细的日志记录

```python
# TTS 重试配置
TTS_MAX_RETRIES = 3
TTS_RETRY_DELAY = 2  # 秒
```

### 2. 升级 edge-tts 版本

`requirements.txt` 已更新：
```
edge-tts>=7.0.2
```

## 🔧 手动修复步骤

### 步骤 1: 升级 edge-tts

```bash
# SSH 登录到服务器
pip install --upgrade edge-tts

# 验证版本
python -c "import edge_tts; print(edge_tts.__version__)"
# 应该 >= 7.0.2
```

### 步骤 2: 运行诊断脚本

```bash
cd /path/to/eeda
python web/diagnose_tts.py
```

诊断脚本会检查：
- ✅ edge-tts 版本
- ✅ ffmpeg 安装
- ✅ 网络连接
- ✅ TTS 生成功能

### 步骤 3: 重启应用

```bash
# 如果使用 Heroku
heroku restart

# 如果使用 systemd
sudo systemctl restart your-app

# 如果使用 Docker
docker-compose restart
```

## 🚀 进一步优化建议

### 1. 添加请求队列（推荐）

如果线上有大量 TTS 请求，建议使用队列控制并发：

```python
import asyncio
from asyncio import Queue

# 创建全局队列
tts_queue = Queue(maxsize=5)

async def tts_worker():
    """TTS 工作线程"""
    while True:
        task = await tts_queue.get()
        try:
            await process_tts_task(task)
        finally:
            tts_queue.task_done()
            await asyncio.sleep(2)  # 请求间隔
```

### 2. 使用代理服务器

如果服务器 IP 被限制，可以配置代理：

```python
# 在环境变量中设置代理
import os
os.environ['HTTPS_PROXY'] = 'http://your-proxy-server:port'
os.environ['HTTP_PROXY'] = 'http://your-proxy-server:port'
```

### 3. 添加缓存机制

对相同文本进行缓存，避免重复请求：

```python
import hashlib

tts_cache = {}

def get_tts_cache_key(text, voice, rate, volume):
    """生成缓存键"""
    content = f"{text}_{voice}_{rate}_{volume}"
    return hashlib.md5(content.encode()).hexdigest()
```

### 4. 监控和告警

添加 TTS 成功率监控：

```python
# 统计 TTS 成功率
tts_stats = {
    'success': 0,
    'failure': 0,
    'last_error': None
}
```

## 📊 测试修复效果

### 本地测试

```bash
# 运行诊断脚本
python web/diagnose_tts.py

# 运行单元测试
python -m pytest web/test_tts_api.py -v
```

### 线上测试

```bash
# 使用 curl 测试 API
curl -X POST http://your-server/api/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "测试文本",
    "voice": "zh-CN-XiaoxiaoNeural"
  }'

# 检查日志
tail -f /var/log/your-app.log | grep TTS
```

## 🔍 日志分析

修复后，日志中应该看到：

### ✅ 成功日志
```
2026-04-17 10:30:15 - web.tts_api - INFO - TTS 生成成功: zh-CN-XiaoxiaoNeural, 文本长度: 10
```

### ⚠️ 重试日志
```
2026-04-17 10:30:15 - web.tts_api - WARNING - TTS 生成失败 (尝试 1/3): 403, message='Invalid response status'
2026-04-17 10:30:15 - web.tts_api - INFO - 等待 2 秒后重试...
2026-04-17 10:30:17 - web.tts_api - INFO - TTS 生成成功: zh-CN-XiaoxiaoNeural, 文本长度: 10
```

### ❌ 失败日志（所有重试都失败）
```
2026-04-17 10:30:15 - web.tts_api - WARNING - TTS 生成失败 (尝试 1/3): 403...
2026-04-17 10:30:17 - web.tts_api - WARNING - TTS 生成失败 (尝试 2/3): 403...
2026-04-17 10:30:19 - web.tts_api - WARNING - TTS 生成失败 (尝试 3/3): 403...
```

## 🆘 仍然失败？

如果按照上述步骤仍然失败：

1. **检查服务器 IP 地区**
   ```bash
   curl ifconfig.me
   # 访问 https://ipinfo.io 查看 IP 信息
   ```

2. **尝试使用其他语音**
   ```python
   # 测试不同的语音
   voices = [
       "zh-CN-XiaoxiaoNeural",
       "zh-CN-YunxiNeural",
       "zh-CN-XiaoyiNeural"
   ]
   ```

3. **考虑替代方案**
   - 百度 TTS API
   - 阿里云 TTS
   - 讯飞 TTS
   - Google Cloud TTS

## 📞 获取帮助

如果问题仍未解决，提供以下信息：

1. 诊断脚本输出：`python web/diagnose_tts.py`
2. 应用日志（最近 100 行）
3. edge-tts 版本：`pip show edge-tts`
4. 服务器环境（操作系统、Python 版本）
5. 完整的错误堆栈
