# -*- coding: UTF-8 -*-
"""
Edge TTS API 服务 - 语音合成与合并

接口:
  POST /api/tts              - 单文本转语音
  POST /api/tts/merge        - 多段语音合成并合并
  GET  /api/tts/voices       - 列出可用的中文语音
  GET  /api/tts/download/<filename> - 下载生成的音频文件
"""

import os
import asyncio
import tempfile
import edge_tts
from pydub import AudioSegment
from flask import request, jsonify, send_from_directory, Blueprint
from pathlib import Path

# 输出目录
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "tts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _run_async(coro):
    """在新的事件循环中运行异步协程"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _generate_tts(text, output_path, voice="zh-CN-XiaoxiaoNeural", rate="+0%", volume="+0%"):
    """异步生成单个 TTS 音频文件"""
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
    await communicate.save(str(output_path))


def _merge_audio_files(file_paths, output_path):
    """使用 pydub 合并多个 mp3 文件"""
    combined = AudioSegment.empty()
    for fp in file_paths:
        segment = AudioSegment.from_mp3(str(fp))
        combined += segment
    combined.export(str(output_path), format="mp3")


def _secure_filename(filename):
    """简单的文件名安全处理"""
    return "".join(c for c in filename if c.isalnum() or c in "._-").strip()


def register_tts_routes(app):
    """将 TTS 路由注册到 Flask app"""

    @app.route('/api/tts', methods=['POST'])
    def api_tts():
        """
        单文本转语音

        请求体 JSON:
        {
            "text": "你好世界",
            "voice": "zh-CN-XiaoxiaoNeural",
            "rate": "+0%",
            "volume": "+0%",
            "output_filename": "tts_output.mp3",
            "return_type": "file" | "json"
        }
        """
        data = request.get_json(force=True) or {}

        text = data.get('text', '')
        if not text:
            return jsonify({'success': False, 'message': '缺少 text 参数'}), 400

        voice = data.get('voice', 'zh-CN-XiaoxiaoNeural')
        rate = data.get('rate', '+0%')
        volume = data.get('volume', '+0%')
        return_type = data.get('return_type', 'json')
        output_filename = data.get('output_filename') or 'tts_output.mp3'
        output_filename = _secure_filename(output_filename)
        if not output_filename.endswith('.mp3'):
            output_filename += '.mp3'

        output_path = OUTPUT_DIR / output_filename

        try:
            _run_async(_generate_tts(text, output_path, voice, rate, volume))
        except Exception as e:
            return jsonify({'success': False, 'message': f'TTS 生成失败: {str(e)}'}), 500

        if return_type == 'file':
            return send_from_directory(str(OUTPUT_DIR), output_filename, as_attachment=False)

        return jsonify({
            'success': True,
            'data': {
                'filename': output_filename,
                'download_url': f'/api/tts/download/{output_filename}'
            },
            'message': 'TTS 生成成功'
        })

    @app.route('/api/tts/merge', methods=['POST'])
    def api_tts_merge():
        """
        多段语音合成并合并为一个音频文件

        请求体 JSON:
        {
            "segments": [
                {"text": "你好", "voice": "zh-CN-XiaoxiaoNeural", "rate": "+0%", "volume": "+0%"},
                {"text": "世界", "voice": "zh-CN-YunxiNeural"}
            ],
            "output_filename": "merged.mp3",
            "return_type": "file" | "json"
        }
        """
        data = request.get_json(force=True) or {}
        segments = data.get('segments', [])

        if not segments or not isinstance(segments, list):
            return jsonify({'success': False, 'message': '缺少 segments 参数或格式错误'}), 400

        return_type = data.get('return_type', 'json')
        output_filename = data.get('output_filename') or 'tts_merged.mp3'
        output_filename = _secure_filename(output_filename)
        if not output_filename.endswith('.mp3'):
            output_filename += '.mp3'

        temp_files = []
        final_output_path = OUTPUT_DIR / output_filename

        try:
            # 1. 为每个 segment 生成临时音频
            for idx, seg in enumerate(segments):
                text = seg.get('text', '')
                if not text:
                    continue
                voice = seg.get('voice', 'zh-CN-XiaoxiaoNeural')
                rate = seg.get('rate', '+0%')
                volume = seg.get('volume', '+0%')

                temp_path = OUTPUT_DIR / f"_temp_{idx}_{output_filename}"
                _run_async(_generate_tts(text, temp_path, voice, rate, volume))
                temp_files.append(temp_path)

            if not temp_files:
                return jsonify({'success': False, 'message': '没有有效的音频片段'}), 400

            # 2. 合并音频
            _merge_audio_files(temp_files, final_output_path)

        except Exception as e:
            return jsonify({'success': False, 'message': f'合并失败: {str(e)}'}), 500
        finally:
            # 3. 清理临时文件
            for tf in temp_files:
                if tf.exists():
                    tf.unlink()

        if return_type == 'file':
            return send_from_directory(str(OUTPUT_DIR), output_filename, as_attachment=False)

        return jsonify({
            'success': True,
            'data': {
                'filename': output_filename,
                'download_url': f'/api/tts/download/{output_filename}'
            },
            'message': '语音合并成功'
        })

    @app.route('/api/tts/voices', methods=['GET'])
    def api_tts_voices():
        """列出所有可用的中文语音"""
        try:
            voices = _run_async(edge_tts.list_voices())
            chinese_voices = [
                {
                    'name': v.get('ShortName'),
                    'friendly_name': v.get('FriendlyName', v.get('Name')),
                    'gender': v.get('Gender'),
                    'locale': v.get('Locale')
                }
                for v in voices
                if v.get('Locale', '').startswith('zh-')
            ]
            return jsonify({
                'success': True,
                'data': chinese_voices,
                'message': ''
            })
        except Exception as e:
            return jsonify({'success': False, 'message': f'获取语音列表失败: {str(e)}'}), 500

    @app.route('/api/tts/download/<filename>', methods=['GET'])
    def api_tts_download(filename):
        """下载生成的音频文件"""
        safe_name = _secure_filename(filename)
        file_path = OUTPUT_DIR / safe_name
        if not file_path.exists():
            return jsonify({'success': False, 'message': '文件不存在'}), 404
        return send_from_directory(str(OUTPUT_DIR), safe_name, as_attachment=False)
