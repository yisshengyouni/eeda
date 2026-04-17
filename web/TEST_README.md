# TTS API 测试说明

## 运行测试

### 运行所有测试
```bash
python -m pytest web/test_tts_api.py -v
```

### 运行特定测试类
```bash
# 只运行工具函数测试
python -m pytest web/test_tts_api.py::TestSecureFilename -v

# 只运行 API 端点测试
python -m pytest web/test_tts_api.py::TestTTSAPIEndpoints -v
```

### 运行特定测试用例
```bash
python -m pytest web/test_tts_api.py::TestTTSAPIEndpoints::test_tts_missing_text -v
```

### 生成测试覆盖率报告
```bash
python -m pytest web/test_tts_api.py --cov=web.tts_api --cov-report=html
```

## 测试覆盖

### 工具函数测试
- `TestSecureFilename`: 文件名安全处理（6个测试）
- `TestRunAsync`: 异步运行函数（2个测试）
- `TestGenerateTTS`: TTS 生成函数（2个测试）
- `TestMergeAudioFiles`: 音频合并函数（3个测试）

### API 端点测试
- `TestTTSAPIEndpoints`: Flask API 端点（16个测试）
  - POST /api/tts（单文本转语音）
  - POST /api/tts/merge（多段语音合并）
  - GET /api/tts/voices（获取语音列表）
  - GET /api/tts/download/<filename>（下载音频文件）

### 集成测试
- `TestTTSIntegration`: 完整工作流程测试（需要网络连接，默认跳过）

## 测试结果

当前测试状态：**29 passed, 1 skipped**

跳过的测试：
- `test_full_tts_workflow`: 需要真实的网络连接来调用 Edge TTS API

## 依赖

测试需要以下依赖：
- pytest
- pydub
- ffmpeg（系统安装）
- flask
- edge-tts

安装测试依赖：
```bash
pip install pytest pydub
```

安装 ffmpeg（macOS）：
```bash
brew install ffmpeg
```
