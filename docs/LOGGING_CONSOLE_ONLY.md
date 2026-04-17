# 日志配置简化说明

## 📋 更新内容

已将 [logging_config.py](file:///Users/zhonghaiqin/Documents/pycharm/eeda/web/logging_config.py) 简化为**仅控制台输出**，移除了文件日志功能。

## ✅ 主要变化

### 简化前
- 支持控制台和文件双输出
- 需要配置日志文件路径、大小、备份数量
- 依赖 `RotatingFileHandler`

### 简化后
- ✅ **仅控制台输出**
- ✅ 更简洁的配置
- ✅ 更少的依赖
- ✅ 更适合容器化部署（Docker、Heroku 等）

## 🚀 使用方式

### 基础使用

```python
from web.logging_config import setup_logging

# 一行代码配置日志
setup_logging(level='INFO')
```

### Flask 应用集成

```python
from flask import Flask
from web.logging_config import setup_flask_logging
from web.tts_api import register_tts_routes

app = Flask(__name__)

# 配置日志
setup_flask_logging(app, level='INFO')

# 注册路由
register_tts_routes(app)

app.run()
```

### 使用预设配置

```python
from web.logging_config import LoggingPresets

# 开发环境 - DEBUG 级别
LoggingPresets.development()

# 生产环境 - INFO 级别
LoggingPresets.production()

# 调试模式 - DEBUG 级别
LoggingPresets.debug()

# 最小化 - 只显示 WARNING 及以上
LoggingPresets.minimal()
```

## 📊 日志输出示例

```
2026-04-17 16:16:14,317 - web.tts_api - INFO - 日志级别: INFO (控制台输出)
2026-04-17 16:16:14,317 - web.tts_api - INFO - 日志配置完成
2026-04-17 16:16:14,318 - web.tts_api - INFO - 📥 收到 TTS 请求
2026-04-17 16:16:14,319 - web.tts_api - INFO - 📝 TTS 参数 - 语音: zh-CN-XiaoxiaoNeural
2026-04-17 16:16:16,500 - web.tts_api - INFO - ✅ TTS 生成成功 - 文件大小: 8064 bytes
```

## 🎯 适用场景

### ✅ 适合
- **本地开发** - 直接查看日志
- **Docker 容器** - 使用 `docker logs` 查看
- **Heroku** - 使用 `heroku logs --tail` 查看
- **Kubernetes** - 使用 `kubectl logs` 查看
- **PM2 管理** - 使用 `pm2 logs` 查看

### ❌ 不适合
- 需要持久化日志文件的场景
- 需要离线分析日志的场景
- 网络不稳定，需要本地缓存日志的场景

## 💡 容器化部署的日志收集

如果使用容器化部署，推荐使用以下方案收集日志：

### Docker

```bash
# 查看日志
docker logs -f <container_id>

# 导出日志
docker logs <container_id> > app.log
```

### Docker Compose

```yaml
version: '3'
services:
  web:
    build: .
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "10"
```

### Heroku

```bash
# 实时查看日志
heroku logs --tail

# 查看最近 1000 行
heroku logs -n 1000
```

### Kubernetes

```bash
# 查看 Pod 日志
kubectl logs -f <pod_name>

# 查看指定容器的日志
kubectl logs -f <pod_name> -c <container_name>
```

## 📝 API 变化

### setup_logging()

**之前:**
```python
setup_logging(
    level='INFO',
    log_file='logs/app.log',
    max_bytes=50*1024*1024,
    backup_count=10
)
```

**现在:**
```python
setup_logging(level='INFO')
```

### setup_flask_logging()

**之前:**
```python
setup_flask_logging(app, level='INFO', log_file='logs/app.log')
```

**现在:**
```python
setup_flask_logging(app, level='INFO')
```

### LoggingPresets

**之前:**
```python
LoggingPresets.production('logs/app.log')
LoggingPresets.debug_with_file('logs/debug.log')
```

**现在:**
```python
LoggingPresets.production()
LoggingPresets.debug()
```

## 🔍 如何保存日志（如需要）

如果确实需要保存日志到文件，可以使用以下方式：

### 方式 1: Shell 重定向

```bash
# 运行应用并保存日志
python main.py > app.log 2>&1

# 使用 nohup
nohup python main.py > app.log 2>&1 &
```

### 方式 2: tee 命令（同时显示和保存）

```bash
python main.py | tee app.log
```

### 方式 3: Docker 日志驱动

Docker 会自动收集 stdout/stderr 的日志，可以通过配置日志驱动来持久化。

### 方式 4: 系统日志服务

使用 systemd、supervisor 等进程管理器来收集和轮转日志。

## ✅ 测试验证

```bash
# 运行测试
python -m pytest web/test_tts_api.py -v

# 结果
29 passed, 1 skipped
```

## 📚 相关文档

- [TTS_LOGGING.md](file:///Users/zhonghaiqin/Documents/pycharm/eeda/docs/TTS_LOGGING.md) - 详细日志说明
- [TTS_LOGGING_SUMMARY.md](file:///Users/zhonghaiqin/Documents/pycharm/eeda/docs/TTS_LOGGING_SUMMARY.md) - 日志增强总结

## 🎉 优势

1. **更简单** - 减少配置项，降低使用门槛
2. **更清晰** - 所有日志集中输出，便于调试
3. **更现代** - 符合 12-Factor App 日志最佳实践
4. **更灵活** - 可以通过外部工具灵活收集和处理日志

现在日志配置更加简洁，专注于控制台输出，更适合现代云原生部署！🚀
