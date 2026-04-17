# TTS API 日志增强总结

## 📋 更新内容

已为 [tts_api.py](file:///Users/zhonghaiqin/Documents/pycharm/eeda/web/tts_api.py) 补充了详细的日志系统，方便线上排查问题。

## ✅ 已完成的改进

### 1. 详细的日志覆盖

#### 工具函数
- ✅ `_run_async()` - 异步任务执行日志
- ✅ `_generate_tts()` - TTS 生成详细日志（重试、错误类型识别）
- ✅ `_merge_audio_files()` - 音频合并进度日志

#### API 端点
- ✅ `POST /api/tts` - 单文本 TTS 请求日志
- ✅ `POST /api/tts/merge` - 音频合并请求日志
- ✅ `GET /api/tts/voices` - 语音列表获取日志
- ✅ `GET /api/tts/download/<filename>` - 文件下载日志

### 2. 智能错误识别

自动识别不同类型的错误并提供针对性日志：

| 错误类型 | 标识 | 说明 |
|---------|------|------|
| 403 | 🔒 | IP 限制、速率限制、Token 失效 |
| 404 | 🔍 | 语音名称无效 |
| Timeout | ⏱️ | 网络连接超时 |
| Connection | 🔌 | 网络不可达或防火墙拦截 |

### 3. 重试机制日志

```
❌ TTS 生成失败 (尝试 1/3): [Exception] 403...
🔒 检测到 403 错误 - 可能是 IP 限制、速率限制或 Token 失效
⏳ 等待 2 秒后重试 (403 错误需要更长等待时间)...

❌ TTS 生成失败 (尝试 2/3): [Exception] 403...
⏳ 等待 4 秒后重试 (403 错误需要更长等待时间)...

✅ TTS 生成成功 (尝试 3/3): zh-CN-XiaoxiaoNeural, 文件大小: 8064 bytes
```

### 4. 业务流程可视化

使用 Emoji 标记不同的操作阶段：

| Emoji | 含义 | 示例 |
|-------|------|------|
| 📥 | 收到请求 | `📥 收到 TTS 请求` |
| 📝 | 参数信息 | `📝 TTS 参数 - 语音: zh-CN-XiaoxiaoNeural` |
| 🔄 | 正在处理 | `🔄 开始生成 TTS 音频...` |
| ✅ | 操作成功 | `✅ TTS 生成成功` |
| ❌ | 操作失败 | `❌ TTS 生成异常` |
| 📤 | 返回响应 | `📤 返回 JSON 响应` |
| 🎵 | 音频片段 | `🎵 生成片段 [1/2]` |
| 🧹 | 清理操作 | `🧹 开始清理 2 个临时文件...` |

## 📁 新增文件

| 文件 | 说明 |
|------|------|
| [tts_api.py](file:///Users/zhonghaiqin/Documents/pycharm/eeda/web/tts_api.py) | 增强的 TTS API（含详细日志） |
| [logging_config.py](file:///Users/zhonghaiqin/Documents/pycharm/eeda/web/logging_config.py) | 日志配置工具 |
| [app_example.py](file:///Users/zhonghaiqin/Documents/pycharm/eeda/web/app_example.py) | Flask 应用集成示例 |
| [TTS_LOGGING.md](file:///Users/zhonghaiqin/Documents/pycharm/eeda/docs/TTS_LOGGING.md) | 日志使用文档 |
| [diagnose_tts.py](file:///Users/zhonghaiqin/Documents/pycharm/eeda/web/diagnose_tts.py) | TTS 诊断工具 |
| [TTS_403_SOLUTION.md](file:///Users/zhonghaiqin/Documents/pycharm/eeda/docs/TTS_403_SOLUTION.md) | 403 错误解决方案 |

## 🚀 使用方式

### 方式 1: 快速开始（开发环境）

```python
from flask import Flask
from web.logging_config import LoggingPresets
from web.tts_api import register_tts_routes

# 开发环境配置
LoggingPresets.development()

app = Flask(__name__)
register_tts_routes(app)
app.run(debug=True)
```

### 方式 2: 生产环境

```python
from flask import Flask
from web.logging_config import LoggingPresets
from web.tts_api import register_tts_routes

# 生产环境配置 - 日志文件自动轮转
LoggingPresets.production('logs/tts_api.log')

app = Flask(__name__)
register_tts_routes(app)
app.run(host='0.0.0.0', port=5000)
```

### 方式 3: 自定义配置

```python
from web.logging_config import setup_logging

setup_logging(
    level='DEBUG',
    log_file='logs/custom.log',
    max_bytes=50*1024*1024,  # 50MB
    backup_count=10
)
```

## 📊 日志输出示例

### 成功请求

```
2026-04-17 16:00:00,000 - web.tts_api - INFO - ============================================================
2026-04-17 16:00:00,001 - web.tts_api - INFO - 📥 收到 TTS 请求
2026-04-17 16:00:00,002 - web.tts_api - INFO - 📝 TTS 参数 - 语音: zh-CN-XiaoxiaoNeural, 语速: +0%, 音量: +0%
2026-04-17 16:00:00,003 - web.tts_api - INFO - 📝 文本长度: 4, 输出文件名: tts_output.mp3
2026-04-17 16:00:00,004 - web.tts_api - INFO - 🔄 开始生成 TTS 音频...
2026-04-17 16:00:02,500 - web.tts_api - INFO - ✅ TTS 生成成功 (尝试 1/3): zh-CN-XiaoxiaoNeural, 文件大小: 8064 bytes
2026-04-17 16:00:02,501 - web.tts_api - INFO - ✅ TTS 音频生成完成
2026-04-17 16:00:02,502 - web.tts_api - INFO - 📤 返回 JSON 响应 - 文件名: tts_output.mp3
```

### 403 错误重试

```
2026-04-17 16:00:00,000 - web.tts_api - INFO - 🔄 开始生成 TTS 音频...
2026-04-17 16:00:01,500 - web.tts_api - WARNING - ❌ TTS 生成失败 (尝试 1/3): 403...
2026-04-17 16:00:01,501 - web.tts_api - WARNING - 🔒 检测到 403 错误 - 可能是 IP 限制、速率限制或 Token 失效
2026-04-17 16:00:01,502 - web.tts_api - INFO - ⏳ 等待 2 秒后重试...
2026-04-17 16:00:03,500 - web.tts_api - INFO - ✅ TTS 生成成功 (尝试 2/3): zh-CN-XiaoxiaoNeural, 文件大小: 8064 bytes
```

### 音频合并

```
2026-04-17 16:00:00,000 - web.tts_api - INFO - 📥 收到 TTS 合并请求
2026-04-17 16:00:00,001 - web.tts_api - INFO - 📝 合并参数 - 片段数: 2, 输出文件: merged.mp3
2026-04-17 16:00:00,002 - web.tts_api - INFO - 🔄 开始生成 2 个音频片段...
2026-04-17 16:00:00,003 - web.tts_api - INFO - 🎵 生成片段 [1/2] - 语音: zh-CN-XiaoxiaoNeural, 文本长度: 2
2026-04-17 16:00:02,000 - web.tts_api - INFO - ✅ TTS 生成成功 (尝试 1/3)
2026-04-17 16:00:02,001 - web.tts_api - INFO - 🎵 生成片段 [2/2] - 语音: zh-CN-YunxiNeural, 文本长度: 2
2026-04-17 16:00:04,000 - web.tts_api - INFO - ✅ 所有音频片段生成完成，共 2 个
2026-04-17 16:00:04,001 - web.tts_api - INFO - 🔄 开始合并音频文件...
2026-04-17 16:00:04,100 - web.tts_api - INFO - ✅ 音频合并成功 - 大小: 8448 bytes, 时长: 2000ms
2026-04-17 16:00:04,101 - web.tts_api - INFO - 🧹 开始清理 2 个临时文件...
```

## 🔍 日志分析命令

### 查找错误

```bash
# 查找所有错误
grep "ERROR" logs/tts_api.log

# 查找 403 错误
grep "403" logs/tts_api.log

# 查找重试记录
grep "重试" logs/tts_api.log
```

### 统计分析

```bash
# 统计成功次数
grep "TTS 生成成功" logs/tts_api.log | wc -l

# 统计失败次数
grep "TTS 生成失败" logs/tts_api.log | wc -l

# 计算成功率
echo "scale=2; $(grep 'TTS 生成成功' logs/tts_api.log | wc -l) * 100 / ($(grep 'TTS 生成成功' logs/tts_api.log | wc -l) + $(grep 'TTS 生成失败' logs/tts_api.log | wc -l))" | bc
```

### 实时监控

```bash
# 实时查看日志
tail -f logs/tts_api.log

# 只查看错误
tail -f logs/tts_api.log | grep "ERROR"

# 只查看 TTS 相关
tail -f logs/tts_api.log | grep "TTS"
```

## 📈 日志级别说明

| 级别 | 说明 | 使用场景 |
|------|------|---------|
| DEBUG | 详细调试信息 | 开发环境、问题排查 |
| INFO | 正常业务流程 | 生产环境默认级别 |
| WARNING | 可恢复的异常 | 重试、跳过等 |
| ERROR | 严重错误 | 处理失败、异常 |
| CRITICAL | 致命错误 | 系统级故障 |

## 🎯 测试验证

所有测试已通过：

```bash
python -m pytest web/test_tts_api.py -v
# 29 passed, 1 skipped
```

## 📚 相关文档

- [TTS_LOGGING.md](file:///Users/zhonghaiqin/Documents/pycharm/eeda/docs/TTS_LOGGING.md) - 详细日志说明
- [TTS_403_SOLUTION.md](file:///Users/zhonghaiqin/Documents/pycharm/eeda/docs/TTS_403_SOLUTION.md) - 403 错误解决方案
- [TEST_README.md](file:///Users/zhonghaiqin/Documents/pycharm/eeda/web/TEST_README.md) - 测试说明

## 💡 最佳实践

1. **开发环境** - 使用 DEBUG 级别，输出到控制台
2. **生产环境** - 使用 INFO 级别，输出到文件（自动轮转）
3. **问题排查** - 临时切换到 DEBUG 级别
4. **性能优化** - 定期清理日志文件，避免磁盘占满
5. **监控告警** - 监控 ERROR 日志，设置告警阈值

## 🎉 总结

现在 TTS API 拥有了完善的日志系统，可以：

✅ 追踪每个请求的完整生命周期  
✅ 快速定位失败原因和错误类型  
✅ 监控重试机制的执行情况  
✅ 分析音频生成的性能指标  
✅ 方便线上问题排查和调试  

所有日志都经过精心设计，既详细又不冗杂，让你对 TTS 服务的运行状态了如指掌！🚀
