# TTS API 日志说明

## 日志级别说明

TTS API 使用了详细的日志系统，方便线上排查问题：

### 日志级别

- **INFO** - 正常的业务流程（请求接收、处理完成等）
- **DEBUG** - 详细的调试信息（参数详情、文件路径等）
- **WARNING** - 可恢复的异常（重试、跳过空片段等）
- **ERROR** - 严重错误（处理失败、异常等）

## 日志示例

### 1. 单文本 TTS 请求（成功）

```
2026-04-17 16:00:00,000 - web.tts_api - INFO - ============================================================
2026-04-17 16:00:00,001 - web.tts_api - INFO - 📥 收到 TTS 请求
2026-04-17 16:00:00,002 - web.tts_api - DEBUG - 请求参数: {'text': '你好世界', 'voice': 'zh-CN-XiaoxiaoNeural'}
2026-04-17 16:00:00,003 - web.tts_api - INFO - 📝 TTS 参数 - 语音: zh-CN-XiaoxiaoNeural, 语速: +0%, 音量: +0%, 返回类型: json
2026-04-17 16:00:00,004 - web.tts_api - INFO - 📝 文本长度: 4, 输出文件名: tts_output.mp3
2026-04-17 16:00:00,005 - web.tts_api - DEBUG - 完整输出路径: /path/to/output/tts/tts_output.mp3
2026-04-17 16:00:00,006 - web.tts_api - INFO - 🔄 开始生成 TTS 音频...
2026-04-17 16:00:00,007 - web.tts_api - DEBUG - 创建新的事件循环运行异步任务
2026-04-17 16:00:00,008 - web.tts_api - INFO - 开始生成 TTS - 语音: zh-CN-XiaoxiaoNeural, 语速: +0%, 音量: +0%, 文本长度: 4
2026-04-17 16:00:00,009 - web.tts_api - DEBUG - TTS 文本内容: 你好世界
2026-04-17 16:00:00,010 - web.tts_api - DEBUG - 输出路径: /path/to/output/tts/tts_output.mp3
2026-04-17 16:00:00,011 - web.tts_api - DEBUG - TTS 尝试 1/3 - 创建 Communicate 对象
2026-04-17 16:00:00,012 - web.tts_api - DEBUG - TTS 尝试 1/3 - 开始保存音频文件
2026-04-17 16:00:02,500 - web.tts_api - INFO - ✅ TTS 生成成功 (尝试 1/3): zh-CN-XiaoxiaoNeural, 文件大小: 8064 bytes, 文本长度: 4
2026-04-17 16:00:02,501 - web.tts_api - DEBUG - 异步任务执行完成
2026-04-17 16:00:02,502 - web.tts_api - INFO - ✅ TTS 音频生成完成
2026-04-17 16:00:02,503 - web.tts_api - INFO - 📤 返回 JSON 响应 - 文件名: tts_output.mp3
```

### 2. TTS 请求（403 错误重试）

```
2026-04-17 16:00:00,000 - web.tts_api - INFO - ============================================================
2026-04-17 16:00:00,001 - web.tts_api - INFO - 📥 收到 TTS 请求
2026-04-17 16:00:00,002 - web.tts_api - INFO - 📝 TTS 参数 - 语音: zh-CN-XiaoxiaoNeural, 语速: +0%, 音量: +0%, 返回类型: json
2026-04-17 16:00:00,003 - web.tts_api - INFO - 📝 文本长度: 10, 输出文件名: test.mp3
2026-04-17 16:00:00,004 - web.tts_api - INFO - 🔄 开始生成 TTS 音频...
2026-04-17 16:00:00,005 - web.tts_api - INFO - 开始生成 TTS - 语音: zh-CN-XiaoxiaoNeural, 语速: +0%, 音量: +0%, 文本长度: 10
2026-04-17 16:00:00,006 - web.tts_api - DEBUG - TTS 尝试 1/3 - 创建 Communicate 对象
2026-04-17 16:00:00,007 - web.tts_api - DEBUG - TTS 尝试 1/3 - 开始保存音频文件
2026-04-17 16:00:01,500 - web.tts_api - WARNING - ❌ TTS 生成失败 (尝试 1/3): [Exception] 403, message='Invalid response status'
2026-04-17 16:00:01,501 - web.tts_api - DEBUG - 失败详情 - 语音: zh-CN-XiaoxiaoNeural, 文本长度: 10, 输出路径: /path/to/output/tts/test.mp3
2026-04-17 16:00:01,502 - web.tts_api - WARNING - 🔒 检测到 403 错误 - 可能是 IP 限制、速率限制或 Token 失效
2026-04-17 16:00:01,503 - web.tts_api - INFO - ⏳ 等待 2 秒后重试 (403 错误需要更长等待时间)...
2026-04-17 16:00:03,504 - web.tts_api - DEBUG - TTS 尝试 2/3 - 创建 Communicate 对象
2026-04-17 16:00:03,505 - web.tts_api - DEBUG - TTS 尝试 2/3 - 开始保存音频文件
2026-04-17 16:00:05,800 - web.tts_api - INFO - ✅ TTS 生成成功 (尝试 2/3): zh-CN-XiaoxiaoNeural, 文件大小: 9216 bytes, 文本长度: 10
2026-04-17 16:00:05,801 - web.tts_api - INFO - ✅ TTS 音频生成完成
2026-04-17 16:00:05,802 - web.tts_api - INFO - 📤 返回 JSON 响应 - 文件名: test.mp3
```

### 3. 合并音频请求

```
2026-04-17 16:00:00,000 - web.tts_api - INFO - ============================================================
2026-04-17 16:00:00,001 - web.tts_api - INFO - 📥 收到 TTS 合并请求
2026-04-17 16:00:00,002 - web.tts_api - DEBUG - 请求参数 - segments 数量: 2
2026-04-17 16:00:00,003 - web.tts_api - INFO - 📝 合并参数 - 片段数: 2, 输出文件: merged.mp3, 返回类型: json
2026-04-17 16:00:00,004 - web.tts_api - INFO - 🔄 开始生成 2 个音频片段...
2026-04-17 16:00:00,005 - web.tts_api - INFO - 🎵 生成片段 [1/2] - 语音: zh-CN-XiaoxiaoNeural, 文本长度: 2
2026-04-17 16:00:00,006 - web.tts_api - INFO - 开始生成 TTS - 语音: zh-CN-XiaoxiaoNeural, 语速: +0%, 音量: +0%, 文本长度: 2
2026-04-17 16:00:02,000 - web.tts_api - INFO - ✅ TTS 生成成功 (尝试 1/3): zh-CN-XiaoxiaoNeural, 文件大小: 4096 bytes, 文本长度: 2
2026-04-17 16:00:02,001 - web.tts_api - DEBUG - 片段 [0] 生成完成
2026-04-17 16:00:02,002 - web.tts_api - INFO - 🎵 生成片段 [2/2] - 语音: zh-CN-YunxiNeural, 文本长度: 2
2026-04-17 16:00:04,000 - web.tts_api - INFO - ✅ TTS 生成成功 (尝试 1/3): zh-CN-YunxiNeural, 文件大小: 4352 bytes, 文本长度: 2
2026-04-17 16:00:04,001 - web.tts_api - DEBUG - 片段 [1] 生成完成
2026-04-17 16:00:04,002 - web.tts_api - INFO - ✅ 所有音频片段生成完成，共 2 个
2026-04-17 16:00:04,003 - web.tts_api - INFO - 🔄 开始合并音频文件...
2026-04-17 16:00:04,004 - web.tts_api - INFO - 开始合并音频文件 - 文件数量: 2, 输出路径: /path/to/output/tts/merged.mp3
2026-04-17 16:00:04,005 - web.tts_api - DEBUG - 加载音频文件 1/2: /path/to/output/tts/_temp_0_merged.mp3
2026-04-17 16:00:04,006 - web.tts_api - DEBUG - 音频文件 1/2 加载成功 - 时长: 1000ms
2026-04-17 16:00:04,007 - web.tts_api - DEBUG - 加载音频文件 2/2: /path/to/output/tts/_temp_1_merged.mp3
2026-04-17 16:00:04,008 - web.tts_api - DEBUG - 音频文件 2/2 加载成功 - 时长: 1000ms
2026-04-17 16:00:04,009 - web.tts_api - INFO - 开始导出合并后的音频文件 - 总时长: 2000ms (2.00s)
2026-04-17 16:00:04,100 - web.tts_api - INFO - ✅ 音频合并成功 - 输出文件: /path/to/output/tts/merged.mp3, 大小: 8448 bytes, 时长: 2000ms
2026-04-17 16:00:04,101 - web.tts_api - INFO - ✅ 音频合并完成
2026-04-17 16:00:04,102 - web.tts_api - DEBUG - 🧹 开始清理 2 个临时文件...
2026-04-17 16:00:04,103 - web.tts_api - DEBUG - 已删除临时文件 [0]: /path/to/output/tts/_temp_0_merged.mp3
2026-04-17 16:00:04,104 - web.tts_api - DEBUG - 已删除临时文件 [1]: /path/to/output/tts/_temp_1_merged.mp3
2026-04-17 16:00:04,105 - web.tts_api - DEBUG - ✅ 临时文件清理完成
2026-04-17 16:00:04,106 - web.tts_api - INFO - 📤 返回合并后的 JSON 响应 - 文件名: merged.mp3
```

## 配置日志级别

### 开发环境（显示所有日志）

```python
import logging

# 配置根日志记录器
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # 输出到控制台
    ]
)
```

### 生产环境（只显示 INFO 及以上）

```python
import logging

# 配置根日志记录器
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tts_api.log'),  # 输出到文件
        logging.StreamHandler()  # 同时输出到控制台
    ]
)
```

### Flask 应用集成日志

```python
from flask import Flask
import logging

app = Flask(__name__)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# 注册 TTS 路由
from web.tts_api import register_tts_routes
register_tts_routes(app)

if __name__ == '__main__':
    app.run(debug=True)
```

## 日志分析技巧

### 1. 查找失败的请求

```bash
# 查找所有错误日志
grep "ERROR" app.log

# 查找 403 错误
grep "403" app.log

# 查找重试记录
grep "重试" app.log
```

### 2. 统计 TTS 成功率

```bash
# 统计成功和失败的次数
grep "TTS 生成成功" app.log | wc -l  # 成功数
grep "TTS 生成失败" app.log | wc -l  # 失败数
```

### 3. 分析性能

```bash
# 查看平均生成时间
grep "TTS 生成成功" app.log | awk '{print $1}'  # 查看时间戳
```

### 4. 实时监控

```bash
# 实时查看日志
tail -f app.log

# 只查看错误
tail -f app.log | grep "ERROR"

# 只查看 TTS 相关
tail -f app.log | grep "TTS"
```

## 日志中包含的 Emoji 说明

| Emoji | 含义 |
|-------|------|
| 📥 | 收到请求 |
| 📝 | 参数信息 |
| 🔄 | 正在处理 |
| ✅ | 操作成功 |
| ❌ | 操作失败 |
| ⚠️ | 警告信息 |
| 🔒 | 403 权限错误 |
| 🔍 | 404 未找到 |
| ⏱️ | 超时错误 |
| 🔌 | 连接错误 |
| ⏳ | 等待重试 |
| 📤 | 返回响应 |
| 🎵 | 音频片段 |
| 🧹 | 清理操作 |

## 性能优化建议

1. **生产环境使用 INFO 级别** - 避免 DEBUG 日志过多影响性能
2. **定期轮转日志文件** - 使用 `RotatingFileHandler`
3. **异步日志** - 高并发场景考虑异步日志
4. **集中式日志** - 使用 ELK 或类似方案集中管理

## 常见问题排查

### 问题 1: TTS 生成失败

查看日志中的错误类型：
- 🔒 403 - IP 限制或速率限制
- 🔍 404 - 语音名称错误
- ⏱️ Timeout - 网络超时
- 🔌 Connection - 网络不可达

### 问题 2: 合并失败

检查每个片段是否成功生成，查看临时文件路径是否正确。

### 问题 3: 文件下载 404

检查 OUTPUT_DIR 配置是否正确，文件是否被意外删除。
