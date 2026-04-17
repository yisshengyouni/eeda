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

# TTS 重试配置
TTS_MAX_RETRIES = 3
TTS_RETRY_DELAY = 2  # 秒


def _run_async(coro):
    """在新的事件循环中运行异步协程"""
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(coro)
        return result
    except Exception as e:
        print(f"[ERROR] 异步任务执行失败: {e}")
        raise
    finally:
        loop.close()


async def _generate_tts(text, output_path, voice="zh-CN-XiaoxiaoNeural", rate="+0%", volume="+0%"):
    """异步生成单个 TTS 音频文件，带重试机制"""
    last_exception = None
    
    print(f"[INFO] 开始生成 TTS - 语音: {voice}, 语速: {rate}, 音量: {volume}, 文本长度: {len(text)}")
    print(f"[DEBUG] TTS 文本内容: {text[:100]}{'...' if len(text) > 100 else ''}")
    print(f"[DEBUG] 输出路径: {output_path}")
    
    for attempt in range(1, TTS_MAX_RETRIES + 1):
        try:
            print(f"[DEBUG] TTS 尝试 {attempt}/{TTS_MAX_RETRIES} - 创建 Communicate 对象")
            communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
            
            print(f"[DEBUG] TTS 尝试 {attempt}/{TTS_MAX_RETRIES} - 开始保存音频文件")
            await communicate.save(str(output_path))
            
            # 验证文件是否成功生成
            if output_path.exists():
                file_size = output_path.stat().st_size
                print(f"[INFO] ✅ TTS 生成成功 (尝试 {attempt}/{TTS_MAX_RETRIES}): {voice}, 文件大小: {file_size} bytes, 文本长度: {len(text)}")
            else:
                print(f"[WARN] ⚠️ TTS 保存完成但文件不存在: {output_path}")
            
            return  # 成功则直接返回
            
        except Exception as e:
            last_exception = e
            error_msg = str(e)
            error_type = type(e).__name__
            
            # 记录详细的重试日志
            print(
                f"[WARN] ❌ TTS 生成失败 (尝试 {attempt}/{TTS_MAX_RETRIES}): [{error_type}] {error_msg}"
            )
            print(f"[DEBUG] 失败详情 - 语音: {voice}, 文本长度: {len(text)}, 输出路径: {output_path}")
            
            # 根据错误类型提供不同的日志
            if "403" in error_msg:
                print("[WARN] 🔒 检测到 403 错误 - 可能是 IP 限制、速率限制或 Token 失效")
            elif "404" in error_msg:
                print("[WARN] 🔍 检测到 404 错误 - 可能是语音名称无效")
            elif "timeout" in error_msg.lower() or "Timeout" in error_msg:
                print("[WARN] ⏱️ 检测到超时错误 - 网络连接不稳定")
            elif "connection" in error_msg.lower():
                print("[WARN] 🔌 检测到连接错误 - 网络不可达或防火墙拦截")
            
            # 如果是 403 错误，等待更长时间后重试
            if "403" in error_msg and attempt < TTS_MAX_RETRIES:
                retry_delay = TTS_RETRY_DELAY * attempt  # 递增延迟
                print(f"[INFO] ⏳ 等待 {retry_delay} 秒后重试 (403 错误需要更长等待时间)...")
                await asyncio.sleep(retry_delay)
            elif attempt < TTS_MAX_RETRIES:
                print(f"[INFO] ⏳ 等待 {TTS_RETRY_DELAY} 秒后重试...")
                await asyncio.sleep(TTS_RETRY_DELAY)
    
    # 所有重试都失败，抛出最后一次异常
    print(f"[ERROR] ❌ TTS 生成最终失败 - 已重试 {TTS_MAX_RETRIES} 次, 最后错误: {last_exception}")
    raise last_exception


def _merge_audio_files(file_paths, output_path):
    """使用 pydub 合并多个 mp3 文件"""
    print(f"[INFO] 开始合并音频文件 - 文件数量: {len(file_paths)}, 输出路径: {output_path}")
    
    combined = AudioSegment.empty()
    total_duration = 0
    
    for idx, fp in enumerate(file_paths, 1):
        try:
            print(f"[DEBUG] 加载音频文件 {idx}/{len(file_paths)}: {fp}")
            segment = AudioSegment.from_mp3(str(fp))
            duration = len(segment)
            total_duration += duration
            print(f"[DEBUG] 音频文件 {idx}/{len(file_paths)} 加载成功 - 时长: {duration}ms")
            combined += segment
        except Exception as e:
            print(f"[ERROR] ❌ 加载音频文件失败 [{idx}/{len(file_paths)}]: {fp}, 错误: {e}")
            raise
    
    print(f"[INFO] 开始导出合并后的音频文件 - 总时长: {total_duration}ms ({total_duration/1000:.2f}s)")
    combined.export(str(output_path), format="mp3")
    
    if output_path.exists():
        file_size = output_path.stat().st_size
        print(f"[INFO] ✅ 音频合并成功 - 输出文件: {output_path}, 大小: {file_size} bytes, 时长: {total_duration}ms")
    else:
        print(f"[ERROR] ❌ 音频合并失败 - 输出文件不存在: {output_path}")


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
        print("=" * 60)
        print("[INFO] 📥 收到 TTS 请求")
        
        data = request.get_json(force=True) or {}
        print(f"[DEBUG] 请求参数: {data}")

        text = data.get('text', '')
        if not text:
            print("[WARN] ❌ 请求缺少 text 参数")
            return jsonify({'success': False, 'message': '缺少 text 参数'}), 400

        voice = data.get('voice', 'zh-CN-XiaoxiaoNeural')
        rate = data.get('rate', '+0%')
        volume = data.get('volume', '+0%')
        return_type = data.get('return_type', 'json')
        output_filename = data.get('output_filename') or 'tts_output.mp3'
        
        print(f"[INFO] 📝 TTS 参数 - 语音: {voice}, 语速: {rate}, 音量: {volume}, 返回类型: {return_type}")
        print(f"[INFO] 📝 文本长度: {len(text)}, 输出文件名: {output_filename}")
        
        output_filename = _secure_filename(output_filename)
        if not output_filename.endswith('.mp3'):
            output_filename += '.mp3'

        output_path = OUTPUT_DIR / output_filename
        print(f"[DEBUG] 完整输出路径: {output_path}")

        try:
            print("[INFO] 🔄 开始生成 TTS 音频...")
            _run_async(_generate_tts(text, output_path, voice, rate, volume))
            print("[INFO] ✅ TTS 音频生成完成")
        except Exception as e:
            print(f"[ERROR] ❌ TTS 生成异常: {e}")
            return jsonify({'success': False, 'message': f'TTS 生成失败: {str(e)}'}), 500

        if return_type == 'file':
            print(f"[INFO] 📤 返回音频文件: {output_filename}")
            return send_from_directory(str(OUTPUT_DIR), output_filename, as_attachment=False)

        print(f"[INFO] 📤 返回 JSON 响应 - 文件名: {output_filename}")
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
        print("=" * 60)
        print("[INFO] 📥 收到 TTS 合并请求")
        
        data = request.get_json(force=True) or {}
        segments = data.get('segments', [])
        
        print(f"[DEBUG] 请求参数 - segments 数量: {len(segments)}")

        if not segments or not isinstance(segments, list):
            print("[WARN] ❌ 请求缺少 segments 参数或格式错误")
            return jsonify({'success': False, 'message': '缺少 segments 参数或格式错误'}), 400

        return_type = data.get('return_type', 'json')
        output_filename = data.get('output_filename') or 'tts_merged.mp3'
        
        print(f"[INFO] 📝 合并参数 - 片段数: {len(segments)}, 输出文件: {output_filename}, 返回类型: {return_type}")
        
        output_filename = _secure_filename(output_filename)
        if not output_filename.endswith('.mp3'):
            output_filename += '.mp3'

        temp_files = []
        final_output_path = OUTPUT_DIR / output_filename
        
        print(f"[DEBUG] 完整输出路径: {final_output_path}")

        try:
            # 1. 为每个 segment 生成临时音频
            print(f"[INFO] 🔄 开始生成 {len(segments)} 个音频片段...")
            for idx, seg in enumerate(segments):
                text = seg.get('text', '')
                if not text:
                    print(f"[DEBUG] 跳过空文本片段 [{idx}]")
                    continue
                    
                voice = seg.get('voice', 'zh-CN-XiaoxiaoNeural')
                rate = seg.get('rate', '+0%')
                volume = seg.get('volume', '+0%')
                
                print(f"[INFO] 🎵 生成片段 [{idx + 1}/{len(segments)}] - 语音: {voice}, 文本长度: {len(text)}")

                temp_path = OUTPUT_DIR / f"_temp_{idx}_{output_filename}"
                print(f"[DEBUG] 片段 [{idx}] 临时文件: {temp_path}")
                
                _run_async(_generate_tts(text, temp_path, voice, rate, volume))
                temp_files.append(temp_path)
                print(f"[DEBUG] 片段 [{idx}] 生成完成")

            if not temp_files:
                print("[WARN] ❌ 没有有效的音频片段")
                return jsonify({'success': False, 'message': '没有有效的音频片段'}), 400

            print(f"[INFO] ✅ 所有音频片段生成完成，共 {len(temp_files)} 个")
            print("[INFO] 🔄 开始合并音频文件...")
            
            # 2. 合并音频
            _merge_audio_files(temp_files, final_output_path)
            print("[INFO] ✅ 音频合并完成")

        except Exception as e:
            print(f"[ERROR] ❌ 合并过程异常: {e}")
            return jsonify({'success': False, 'message': f'合并失败: {str(e)}'}), 500
        finally:
            # 3. 清理临时文件
            print(f"[DEBUG] 🧹 开始清理 {len(temp_files)} 个临时文件...")
            for idx, tf in enumerate(temp_files):
                try:
                    if tf.exists():
                        tf.unlink()
                        print(f"[DEBUG] 已删除临时文件 [{idx}]: {tf}")
                except Exception as e:
                    print(f"[WARN] ⚠️ 删除临时文件失败 [{idx}]: {tf}, 错误: {e}")
            print("[DEBUG] ✅ 临时文件清理完成")

        if return_type == 'file':
            print(f"[INFO] 📤 返回合并后的音频文件: {output_filename}")
            return send_from_directory(str(OUTPUT_DIR), output_filename, as_attachment=False)

        print(f"[INFO] 📤 返回合并后的 JSON 响应 - 文件名: {output_filename}")
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
        print("=" * 60)
        print("[INFO] 📥 收到获取语音列表请求")
        
        try:
            print("[DEBUG] 🔄 开始获取 Edge TTS 语音列表...")
            voices = _run_async(edge_tts.list_voices())
            print(f"[DEBUG] 获取到 {len(voices)} 个语音")
            
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
            
            print(f"[INFO] ✅ 成功获取 {len(chinese_voices)} 个中文语音")
            print(f"[DEBUG] 中文语音列表: {[v['name'] for v in chinese_voices]}")
            
            return jsonify({
                'success': True,
                'data': chinese_voices,
                'message': ''
            })
        except Exception as e:
            print(f"[ERROR] ❌ 获取语音列表失败: {e}")
            return jsonify({'success': False, 'message': f'获取语音列表失败: {str(e)}'}), 500

    @app.route('/api/tts/download/<filename>', methods=['GET'])
    def api_tts_download(filename):
        """下载生成的音频文件"""
        print("=" * 60)
        print(f"[INFO] 📥 收到下载请求 - 文件名: {filename}")
        
        safe_name = _secure_filename(filename)
        file_path = OUTPUT_DIR / safe_name
        
        print(f"[DEBUG] 安全文件名: {safe_name}")
        print(f"[DEBUG] 完整文件路径: {file_path}")
        
        if not file_path.exists():
            print(f"[WARN] ❌ 文件不存在: {file_path}")
            return jsonify({'success': False, 'message': '文件不存在'}), 404
        
        file_size = file_path.stat().st_size
        print(f"[INFO] ✅ 文件存在，大小: {file_size} bytes，准备返回")
        
        return send_from_directory(str(OUTPUT_DIR), safe_name, as_attachment=False)
