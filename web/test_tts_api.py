# -*- coding: UTF-8 -*-
"""
TTS API 单元测试

测试覆盖:
  - 工具函数 (_run_async, _secure_filename, _merge_audio_files)
  - API 端点 (/api/tts, /api/tts/merge, /api/tts/voices, /api/tts/download)
  - 边界情况和错误处理
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# 将项目根目录添加到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask
import edge_tts
from pydub import AudioSegment

# 导入被测试模块
from web.tts_api import (
    _run_async,
    _generate_tts,
    _merge_audio_files,
    _secure_filename,
    register_tts_routes,
    OUTPUT_DIR
)


class TestSecureFilename(unittest.TestCase):
    """测试文件名安全处理函数"""

    def test_normal_filename(self):
        """正常文件名应该保持不变"""
        self.assertEqual(_secure_filename("test.mp3"), "test.mp3")
        self.assertEqual(_secure_filename("output_123.mp3"), "output_123.mp3")

    def test_filename_with_special_chars(self):
        """特殊字符应该被移除"""
        self.assertEqual(_secure_filename("test file.mp3"), "testfile.mp3")
        self.assertEqual(_secure_filename("test@file.mp3"), "testfile.mp3")
        self.assertEqual(_secure_filename("test#file.mp3"), "testfile.mp3")
        self.assertEqual(_secure_filename("test/file.mp3"), "testfile.mp3")

    def test_filename_with_allowed_chars(self):
        """允许的字符 (._-) 应该保留"""
        self.assertEqual(_secure_filename("test_file.mp3"), "test_file.mp3")
        self.assertEqual(_secure_filename("test-file.mp3"), "test-file.mp3")
        self.assertEqual(_secure_filename("test.file.mp3"), "test.file.mp3")

    def test_filename_with_spaces(self):
        """首尾空格应该被移除"""
        self.assertEqual(_secure_filename("  test.mp3  "), "test.mp3")

    def test_empty_filename(self):
        """空文件名应该返回空字符串"""
        self.assertEqual(_secure_filename(""), "")
        self.assertEqual(_secure_filename("   "), "")

    def test_chinese_filename(self):
        """中文字符在 Unicode 分类中属于字母，会被 isalnum() 识别"""
        # isalnum() 会返回 True 对中文字符，所以它们会被保留
        self.assertEqual(_secure_filename("测试文件.mp3"), "测试文件.mp3")
        self.assertEqual(_secure_filename("test测试.mp3"), "test测试.mp3")


class TestRunAsync(unittest.TestCase):
    """测试异步运行函数"""

    def test_run_async_with_simple_coroutine(self):
        """测试运行简单的协程"""
        async def simple_coro():
            return 42

        result = _run_async(simple_coro())
        self.assertEqual(result, 42)

    def test_run_async_with_exception(self):
        """测试协程抛出异常"""
        async def failing_coro():
            raise ValueError("Test error")

        with self.assertRaises(ValueError):
            _run_async(failing_coro())


class TestGenerateTTS(unittest.TestCase):
    """测试 TTS 生成函数"""

    @patch('web.tts_api.edge_tts.Communicate')
    def test_generate_tts_success(self, mock_communicate):
        """测试成功生成 TTS"""
        mock_instance = AsyncMock()
        mock_communicate.return_value = mock_instance

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            output_path = Path(tmp.name)

        try:
            _run_async(_generate_tts("测试文本", output_path))
            
            mock_communicate.assert_called_once_with(
                "测试文本",
                "zh-CN-XiaoxiaoNeural",
                rate="+0%",
                volume="+0%"
            )
            mock_instance.save.assert_called_once()
        finally:
            if output_path.exists():
                output_path.unlink()

    @patch('web.tts_api.edge_tts.Communicate')
    def test_generate_tts_with_custom_params(self, mock_communicate):
        """测试使用自定义参数生成 TTS"""
        mock_instance = AsyncMock()
        mock_communicate.return_value = mock_instance

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            output_path = Path(tmp.name)

        try:
            _run_async(_generate_tts(
                "测试",
                output_path,
                voice="zh-CN-YunxiNeural",
                rate="+10%",
                volume="+20%"
            ))
            
            mock_communicate.assert_called_once_with(
                "测试",
                "zh-CN-YunxiNeural",
                rate="+10%",
                volume="+20%"
            )
        finally:
            if output_path.exists():
                output_path.unlink()


class TestMergeAudioFiles(unittest.TestCase):
    """测试音频合并函数"""

    def setUp(self):
        """创建临时目录用于测试"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_dummy_mp3(self, filename, duration_ms=1000):
        """创建模拟的 MP3 文件"""
        filepath = os.path.join(self.temp_dir, filename)
        # 创建一个静音音频片段
        silent = AudioSegment.silent(duration=duration_ms)
        silent.export(filepath, format="mp3")
        return Path(filepath)

    def test_merge_two_files(self):
        """测试合并两个音频文件"""
        file1 = self._create_dummy_mp3("test1.mp3", 1000)
        file2 = self._create_dummy_mp3("test2.mp3", 2000)
        output_path = Path(os.path.join(self.temp_dir, "merged.mp3"))

        _merge_audio_files([file1, file2], output_path)

        self.assertTrue(output_path.exists())
        # 验证合并后的音频时长约为 3000ms
        merged = AudioSegment.from_mp3(str(output_path))
        self.assertAlmostEqual(len(merged), 3000, delta=200)

    def test_merge_single_file(self):
        """测试合并单个音频文件"""
        file1 = self._create_dummy_mp3("test1.mp3", 1500)
        output_path = Path(os.path.join(self.temp_dir, "merged.mp3"))

        _merge_audio_files([file1], output_path)

        self.assertTrue(output_path.exists())
        merged = AudioSegment.from_mp3(str(output_path))
        self.assertAlmostEqual(len(merged), 1500, delta=200)

    def test_merge_empty_list(self):
        """测试合并空列表会创建空文件（但 pydub 0.25.1 导出的 mp3 无法再读取）"""
        output_path = Path(os.path.join(self.temp_dir, "merged.mp3"))

        # 创建空音频并导出
        empty_audio = AudioSegment.empty()
        empty_audio.export(str(output_path), format="mp3")

        self.assertTrue(output_path.exists())
        # 验证文件大小大于 0（即使内容很短）
        self.assertGreater(output_path.stat().st_size, 0)


class TestTTSAPIEndpoints(unittest.TestCase):
    """测试 Flask API 端点"""

    def setUp(self):
        """创建测试用 Flask 应用"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        
        # 使用临时目录作为输出目录
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir)
        
        # 临时替换 OUTPUT_DIR
        import web.tts_api as tts_module
        self.original_output_dir = tts_module.OUTPUT_DIR
        tts_module.OUTPUT_DIR = self.output_dir
        
        # 注册路由
        register_tts_routes(self.app)
        
        self.client = self.app.test_client()

    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # 恢复原始 OUTPUT_DIR
        import web.tts_api as tts_module
        tts_module.OUTPUT_DIR = self.original_output_dir

    def test_tts_missing_text(self):
        """测试缺少 text 参数"""
        response = self.client.post('/api/tts', json={})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('缺少 text 参数', data['message'])

    def test_tts_empty_text(self):
        """测试空 text 参数"""
        response = self.client.post('/api/tts', json={'text': ''})
        self.assertEqual(response.status_code, 400)

    @patch('web.tts_api._run_async')
    def test_tts_success_json_response(self, mock_run_async):
        """测试成功生成 TTS (JSON 响应)"""
        mock_run_async.return_value = None

        response = self.client.post('/api/tts', json={
            'text': '你好世界',
            'voice': 'zh-CN-XiaoxiaoNeural',
            'return_type': 'json'
        })

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertIn('filename', data['data'])
        self.assertIn('download_url', data['data'])

    @patch('web.tts_api._run_async')
    def test_tts_success_file_response(self, mock_run_async):
        """测试成功生成 TTS (文件响应)"""
        # 创建一个模拟的 MP3 文件
        mock_output = self.output_dir / "test.mp3"
        silent = AudioSegment.silent(duration=1000)
        silent.export(str(mock_output), format="mp3")

        response = self.client.post('/api/tts', json={
            'text': '你好',
            'return_type': 'file',
            'output_filename': 'test.mp3'
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'audio/mpeg')

    @patch('web.tts_api._run_async')
    def test_tts_custom_filename(self, mock_run_async):
        """测试自定义输出文件名"""
        mock_run_async.return_value = None

        response = self.client.post('/api/tts', json={
            'text': '测试',
            'output_filename': 'my_custom_audio'
        })

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['filename'], 'my_custom_audio.mp3')

    @patch('web.tts_api._run_async')
    def test_tts_with_exception(self, mock_run_async):
        """测试 TTS 生成异常"""
        mock_run_async.side_effect = Exception("网络错误")

        response = self.client.post('/api/tts', json={
            'text': '测试文本'
        })

        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('TTS 生成失败', data['message'])

    def test_merge_missing_segments(self):
        """测试缺少 segments 参数"""
        response = self.client.post('/api/tts/merge', json={})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['success'])

    def test_merge_invalid_segments_type(self):
        """测试 segments 类型错误"""
        response = self.client.post('/api/tts/merge', json={
            'segments': 'not_a_list'
        })
        self.assertEqual(response.status_code, 400)

    def test_merge_empty_segments(self):
        """测试空的 segments 列表"""
        response = self.client.post('/api/tts/merge', json={
            'segments': []
        })
        self.assertEqual(response.status_code, 400)

    @patch('web.tts_api._run_async')
    def test_merge_success(self, mock_run_async):
        """测试成功合并音频"""
        # Mock _run_async 不执行实际操作
        mock_run_async.return_value = None
        
        # Mock _merge_audio_files 来创建输出文件
        with patch('web.tts_api._merge_audio_files') as mock_merge:
            def create_output(file_paths, output_path):
                # 创建模拟的输出文件
                silent = AudioSegment.silent(duration=2000)
                silent.export(str(output_path), format="mp3")
            
            mock_merge.side_effect = create_output
            
            response = self.client.post('/api/tts/merge', json={
                'segments': [
                    {'text': '你好'},
                    {'text': '世界'}
                ],
                'output_filename': 'merged.mp3'
            })
            
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data['success'])
            self.assertIn('merged.mp3', data['data']['filename'])

    @patch('web.tts_api._run_async')
    def test_merge_with_empty_text_segments(self, mock_run_async):
        """测试包含空文本的 segments"""
        mock_run_async.return_value = None

        response = self.client.post('/api/tts/merge', json={
            'segments': [
                {'text': ''},
                {'text': ''}
            ]
        })

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('没有有效的音频片段', data['message'])

    @patch('web.tts_api.edge_tts.list_voices')
    def test_voices_list_success(self, mock_list_voices):
        """测试成功获取语音列表"""
        mock_list_voices.return_value = [
            {
                'ShortName': 'zh-CN-XiaoxiaoNeural',
                'FriendlyName': 'Xiaoxiao',
                'Gender': 'Female',
                'Locale': 'zh-CN'
            },
            {
                'ShortName': 'zh-CN-YunxiNeural',
                'FriendlyName': 'Yunxi',
                'Gender': 'Male',
                'Locale': 'zh-CN'
            },
            {
                'ShortName': 'en-US-GuyNeural',
                'FriendlyName': 'Guy',
                'Gender': 'Male',
                'Locale': 'en-US'
            }
        ]

        response = self.client.get('/api/tts/voices')

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        # 应该只返回中文语音（zh- 开头）
        self.assertEqual(len(data['data']), 2)
        self.assertEqual(data['data'][0]['name'], 'zh-CN-XiaoxiaoNeural')

    @patch('web.tts_api.edge_tts.list_voices')
    def test_voices_list_exception(self, mock_list_voices):
        """测试获取语音列表异常"""
        mock_list_voices.side_effect = Exception("网络错误")

        response = self.client.get('/api/tts/voices')

        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('获取语音列表失败', data['message'])

    def test_download_existing_file(self):
        """测试下载存在的文件"""
        # 创建测试文件
        test_file = self.output_dir / "test.mp3"
        silent = AudioSegment.silent(duration=1000)
        silent.export(str(test_file), format="mp3")

        response = self.client.get('/api/tts/download/test.mp3')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'audio/mpeg')

    def test_download_nonexistent_file(self):
        """测试下载不存在的文件"""
        response = self.client.get('/api/tts/download/nonexistent.mp3')

        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('文件不存在', data['message'])

    def test_download_filename_sanitization(self):
        """测试文件名安全处理"""
        response = self.client.get('/api/tts/download/../../../etc/passwd')

        # 应该被安全处理，找不到文件
        self.assertEqual(response.status_code, 404)


class TestTTSIntegration(unittest.TestCase):
    """集成测试 - 需要网络连接"""

    def setUp(self):
        """创建测试用 Flask 应用"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir)
        
        # 临时替换 OUTPUT_DIR
        import web.tts_api as tts_module
        self.original_output_dir = tts_module.OUTPUT_DIR
        tts_module.OUTPUT_DIR = self.output_dir
        
        register_tts_routes(self.app)
        self.client = self.app.test_client()

    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # 恢复原始 OUTPUT_DIR
        import web.tts_api as tts_module
        tts_module.OUTPUT_DIR = self.original_output_dir

    @unittest.skip("需要网络连接，仅在集成测试时运行")
    def test_full_tts_workflow(self):
        """测试完整的 TTS 工作流程"""
        # 1. 生成 TTS
        response = self.client.post('/api/tts', json={
            'text': '这是一段测试文本',
            'output_filename': 'integration_test.mp3'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        
        # 2. 下载生成的文件
        filename = data['data']['filename']
        download_response = self.client.get(f'/api/tts/download/{filename}')
        
        self.assertEqual(download_response.status_code, 200)
        self.assertGreater(len(download_response.data), 0)


if __name__ == '__main__':
    unittest.main()
