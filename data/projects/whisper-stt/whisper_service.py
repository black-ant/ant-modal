"""
Whisper 语音转文字服务
使用 OpenAI Whisper 模型进行语音识别
"""
import modal

app = modal.App("whisper-stt")

# 构建镜像
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")  # Whisper 需要 ffmpeg
    .pip_install(
        "openai-whisper",
        "torch==2.1.0",
    )
)

# 模型缓存
model_volume = modal.Volume.from_name("whisper-models", create_if_missing=True)


@app.cls(
    image=image,
    gpu="T4",  # Whisper 不需要太大的 GPU
    volumes={"/models": model_volume},
    timeout=600,
)
class WhisperSTT:
    @modal.enter()
    def load_model(self):
        """加载 Whisper 模型"""
        import whisper
        
        print("🎤 加载 Whisper 模型...")
        
        # 可选: tiny, base, small, medium, large
        self.model = whisper.load_model(
            "medium",
            download_root="/models"
        )
        
        print("✓ 模型加载完成")
    
    @modal.method()
    def transcribe(
        self,
        audio_data: bytes,
        language: str = None,
        task: str = "transcribe"
    ) -> dict:
        """
        语音转文字
        
        Args:
            audio_data: 音频文件字节数据
            language: 语言代码 (zh, en, ja 等)，None 为自动检测
            task: "transcribe" 或 "translate" (翻译成英文)
        
        Returns:
            转录结果
        """
        import tempfile
        import os
        
        # 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio_data)
            temp_path = f.name
        
        try:
            print(f"🎤 转录音频...")
            
            result = self.model.transcribe(
                temp_path,
                language=language,
                task=task,
                fp16=True
            )
            
            print(f"✓ 转录完成")
            
            return {
                "text": result["text"],
                "language": result.get("language"),
                "segments": [
                    {
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"]
                    }
                    for seg in result.get("segments", [])
                ]
            }
        finally:
            os.unlink(temp_path)


@app.function(image=image)
@modal.web_endpoint(method="POST")
def transcribe_audio(audio: bytes, language: str = None):
    """
    Web API 端点
    
    POST /transcribe_audio
    Content-Type: audio/wav (或其他音频格式)
    
    Query params:
    - language: 语言代码 (可选)
    """
    whisper = WhisperSTT()
    result = whisper.transcribe.remote(audio, language=language)
    return result


@app.local_entrypoint()
def main(audio_file: str):
    """
    本地测试
    
    使用方法:
    modal run whisper_service.py --audio-file=audio.mp3
    """
    whisper = WhisperSTT()
    
    with open(audio_file, "rb") as f:
        audio_data = f.read()
    
    result = whisper.transcribe.remote(audio_data)
    
    print(f"\n📝 转录结果:\n{result['text']}\n")
    print(f"语言: {result['language']}")
    
    if result.get('segments'):
        print("\n时间轴:")
        for seg in result['segments'][:5]:  # 只显示前5段
            print(f"  [{seg['start']:.2f}s - {seg['end']:.2f}s] {seg['text']}")
