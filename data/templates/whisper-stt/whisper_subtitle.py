"""
视频字幕自动生成
业务场景：视频平台/自媒体需要为视频添加字幕

解决的问题：
- 手动添加字幕每小时视频需要 4-6 小时
- 外包字幕成本高，质量不稳定
- 多语言字幕需求增加，人工处理难以满足

这个例子展示：
- 从视频中提取音频并转录
- 生成带时间戳的 SRT 字幕文件
- 支持多语言转录和翻译
- 批量处理多个视频
"""
import modal
import io
from datetime import datetime

app = modal.App("whisper-subtitle")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install(
        "openai-whisper",
        "torch==2.1.0",
    )
)

model_volume = modal.Volume.from_name("whisper-models", create_if_missing=True)
output_volume = modal.Volume.from_name("video-subtitles", create_if_missing=True)


def format_timestamp(seconds: float) -> str:
    """将秒数转换为 SRT 时间戳格式 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(segments: list[dict]) -> str:
    """生成 SRT 格式字幕"""
    srt_content = []
    
    for i, seg in enumerate(segments, 1):
        start_time = format_timestamp(seg["start"])
        end_time = format_timestamp(seg["end"])
        text = seg["text"].strip()
        
        srt_content.append(f"{i}")
        srt_content.append(f"{start_time} --> {end_time}")
        srt_content.append(text)
        srt_content.append("")  # 空行分隔
    
    return "\n".join(srt_content)


def generate_vtt(segments: list[dict]) -> str:
    """生成 WebVTT 格式字幕"""
    vtt_content = ["WEBVTT", ""]
    
    for i, seg in enumerate(segments, 1):
        start_time = format_timestamp(seg["start"]).replace(",", ".")
        end_time = format_timestamp(seg["end"]).replace(",", ".")
        text = seg["text"].strip()
        
        vtt_content.append(f"{i}")
        vtt_content.append(f"{start_time} --> {end_time}")
        vtt_content.append(text)
        vtt_content.append("")
    
    return "\n".join(vtt_content)


@app.cls(
    image=image,
    gpu="T4",
    volumes={"/models": model_volume, "/output": output_volume},
    timeout=1800,
)
class SubtitleGenerator:
    @modal.enter()
    def load_model(self):
        import whisper
        
        print("🎤 加载 Whisper 模型...")
        # large 模型精度更高，适合字幕生成
        self.model = whisper.load_model("medium", download_root="/models")
        print("✓ 模型加载完成")
    
    @modal.method()
    def generate_subtitle(
        self,
        audio_data: bytes,
        language: str = None,
        task: str = "transcribe",
        output_format: str = "srt"
    ) -> dict:
        """
        生成视频字幕
        
        Args:
            audio_data: 音频数据（可从视频提取）
            language: 源语言（None 自动检测）
            task: "transcribe"(转录) 或 "translate"(翻译成英文)
            output_format: "srt" 或 "vtt"
        
        Returns:
            字幕内容和元数据
        """
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio_data)
            temp_path = f.name
        
        try:
            print(f"🎬 生成字幕 (语言: {language or '自动检测'}, 任务: {task})")
            
            result = self.model.transcribe(
                temp_path,
                language=language,
                task=task,
                fp16=True,
                verbose=False
            )
            
            segments = [
                {
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"]
                }
                for seg in result.get("segments", [])
            ]
            
            # 生成字幕文件
            if output_format == "vtt":
                subtitle_content = generate_vtt(segments)
            else:
                subtitle_content = generate_srt(segments)
            
            duration = segments[-1]["end"] if segments else 0
            
            print(f"✓ 字幕生成完成: {len(segments)} 条, {duration/60:.1f} 分钟")
            
            return {
                "subtitle": subtitle_content,
                "format": output_format,
                "language": result.get("language"),
                "segments_count": len(segments),
                "duration_seconds": duration,
                "segments": segments  # 原始分段数据
            }
            
        finally:
            os.unlink(temp_path)
    
    @modal.method()
    def generate_bilingual_subtitle(
        self,
        audio_data: bytes,
        source_language: str = "zh",
        output_format: str = "srt"
    ) -> dict:
        """
        生成双语字幕（原文 + 英文翻译）
        """
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio_data)
            temp_path = f.name
        
        try:
            # 转录原文
            print("🎬 转录原文...")
            original = self.model.transcribe(
                temp_path,
                language=source_language,
                task="transcribe",
                fp16=True
            )
            
            # 翻译成英文
            print("🌐 翻译成英文...")
            translated = self.model.transcribe(
                temp_path,
                language=source_language,
                task="translate",
                fp16=True
            )
            
            # 合并双语字幕
            bilingual_segments = []
            for orig_seg, trans_seg in zip(
                original.get("segments", []),
                translated.get("segments", [])
            ):
                bilingual_segments.append({
                    "start": orig_seg["start"],
                    "end": orig_seg["end"],
                    "text": f"{orig_seg['text'].strip()}\n{trans_seg['text'].strip()}"
                })
            
            if output_format == "vtt":
                subtitle_content = generate_vtt(bilingual_segments)
            else:
                subtitle_content = generate_srt(bilingual_segments)
            
            return {
                "subtitle": subtitle_content,
                "format": output_format,
                "type": "bilingual",
                "source_language": source_language,
                "segments_count": len(bilingual_segments)
            }
            
        finally:
            os.unlink(temp_path)


@app.function(
    image=image,
    volumes={"/output": output_volume},
    timeout=3600
)
def batch_generate_subtitles(
    videos: list[dict],
    language: str = None,
    output_format: str = "srt"
) -> dict:
    """
    批量生成字幕
    
    Args:
        videos: 视频列表 [{"name": "video1", "audio_data": bytes}]
        language: 语言
        output_format: 输出格式
    """
    import os
    
    generator = SubtitleGenerator()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"/output/batch_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
    results = {
        "total": len(videos),
        "success": 0,
        "failed": 0,
        "files": []
    }
    
    print(f"🎬 批量生成字幕: {len(videos)} 个视频")
    
    for i, video in enumerate(videos, 1):
        print(f"\n[{i}/{len(videos)}] 处理: {video['name']}")
        
        try:
            result = generator.generate_subtitle.remote(
                audio_data=video["audio_data"],
                language=language,
                output_format=output_format
            )
            
            # 保存字幕文件
            ext = "vtt" if output_format == "vtt" else "srt"
            filename = f"{video['name']}.{ext}"
            filepath = f"{output_dir}/{filename}"
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(result["subtitle"])
            
            results["files"].append({
                "video": video["name"],
                "subtitle_file": filename,
                "segments": result["segments_count"],
                "duration": result["duration_seconds"]
            })
            results["success"] += 1
            
            print(f"  ✓ 完成: {result['segments_count']} 条字幕")
            
        except Exception as e:
            results["failed"] += 1
            print(f"  ✗ 失败: {str(e)}")
    
    output_volume.commit()
    
    print(f"\n✅ 批量处理完成: {results['success']} 成功, {results['failed']} 失败")
    return results


@app.function(image=image)
@modal.web_endpoint(method="POST")
def subtitle_api(
    audio: bytes,
    language: str = None,
    format: str = "srt",
    bilingual: bool = False
):
    """
    字幕生成 API
    
    POST /subtitle_api
    Content-Type: audio/*
    Query params:
    - language: 源语言 (zh, en, ja 等)
    - format: srt 或 vtt
    - bilingual: true 生成双语字幕
    """
    generator = SubtitleGenerator()
    
    if bilingual:
        result = generator.generate_bilingual_subtitle.remote(
            audio_data=audio,
            source_language=language or "zh",
            output_format=format
        )
    else:
        result = generator.generate_subtitle.remote(
            audio_data=audio,
            language=language,
            output_format=format
        )
    
    return {
        "status": "success",
        "subtitle": result["subtitle"],
        "format": result["format"],
        "segments_count": result["segments_count"]
    }


@app.local_entrypoint()
def main():
    """使用说明"""
    print("🎬 视频字幕自动生成")
    print("=" * 50)
    print("\n使用方法:")
    print("1. 部署服务: modal deploy whisper_subtitle.py")
    print("\n2. 调用 API 生成字幕:")
    print("   curl -X POST -H 'Content-Type: audio/mp3' \\")
    print("        --data-binary @video_audio.mp3 \\")
    print("        'https://your-app--subtitle-api.modal.run?format=srt'")
    print("\n3. 生成双语字幕:")
    print("   ...?language=zh&bilingual=true")
    print("\n💡 提示:")
    print("1. 支持 SRT 和 WebVTT 两种格式")
    print("2. 可先用 ffmpeg 从视频提取音频")
    print("3. 双语字幕适合学习类/国际化视频")

