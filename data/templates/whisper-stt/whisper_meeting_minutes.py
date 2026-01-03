"""
会议纪要自动生成
业务场景：每次会议后需要整理会议纪要，耗时且容易遗漏

解决的问题：
- 一小时会议，整理纪要需要2小时
- 经常漏掉重要信息和待办事项
- 不同人整理的格式不统一

这个例子展示：
- 会议录音转文字
- 自动提取关键信息和待办事项
- 生成结构化会议纪要
- 按发言人分段（如果提供）
"""
import modal
import json
from datetime import datetime
import re

app = modal.App("whisper-meeting-minutes")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install(
        "openai-whisper",
        "torch==2.1.0",
    )
)

model_volume = modal.Volume.from_name("whisper-models", create_if_missing=True)
output_volume = modal.Volume.from_name("meeting-minutes", create_if_missing=True)


@app.cls(
    image=image,
    gpu="T4",
    volumes={"/models": model_volume, "/output": output_volume},
    timeout=1800,  # 会议录音可能较长
)
class MeetingTranscriber:
    @modal.enter()
    def load_model(self):
        import whisper
        
        print("🎤 加载 Whisper 模型...")
        self.model = whisper.load_model("medium", download_root="/models")
        print("✓ 模型加载完成")
    
    @modal.method()
    def transcribe_meeting(
        self,
        audio_data: bytes,
        language: str = "zh",
        meeting_info: dict = None
    ) -> dict:
        """
        转录会议录音
        
        Args:
            audio_data: 音频数据
            language: 语言代码
            meeting_info: 会议信息 {"title": "...", "date": "...", "participants": [...]}
        """
        import tempfile
        import os
        
        if meeting_info is None:
            meeting_info = {}
        
        # 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio_data)
            temp_path = f.name
        
        try:
            print("🎤 开始转录会议录音...")
            
            result = self.model.transcribe(
                temp_path,
                language=language,
                task="transcribe",
                fp16=True
            )
            
            print("✓ 转录完成")
            
            # 构建转录结果
            transcript = {
                "full_text": result["text"],
                "segments": [
                    {
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"].strip()
                    }
                    for seg in result.get("segments", [])
                ],
                "duration_minutes": result.get("segments", [{}])[-1].get("end", 0) / 60 if result.get("segments") else 0
            }
            
            return transcript
            
        finally:
            os.unlink(temp_path)
    
    @modal.method()
    def extract_key_points(self, transcript_text: str) -> dict:
        """
        从转录文本中提取关键信息
        
        使用规则提取（可以替换为 LLM 提取）
        """
        key_points = {
            "decisions": [],      # 决策事项
            "action_items": [],   # 待办事项
            "questions": [],      # 提出的问题
            "key_topics": [],     # 关键议题
        }
        
        # 简单的规则提取（实际场景可用 LLM）
        sentences = re.split(r'[。！？]', transcript_text)
        
        decision_keywords = ["决定", "确定", "同意", "通过", "批准"]
        action_keywords = ["需要", "负责", "跟进", "完成", "处理", "安排"]
        question_keywords = ["？", "怎么", "如何", "是否", "能不能"]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # 检测决策
            if any(kw in sentence for kw in decision_keywords):
                key_points["decisions"].append(sentence)
            
            # 检测待办
            if any(kw in sentence for kw in action_keywords):
                key_points["action_items"].append(sentence)
            
            # 检测问题
            if any(kw in sentence for kw in question_keywords):
                key_points["questions"].append(sentence)
        
        # 去重并限制数量
        for key in key_points:
            key_points[key] = list(set(key_points[key]))[:10]
        
        return key_points


@app.function(
    image=image,
    volumes={"/output": output_volume},
    timeout=3600
)
def generate_meeting_minutes(
    audio_data: bytes,
    meeting_info: dict = None,
    language: str = "zh"
) -> dict:
    """
    生成完整的会议纪要
    
    Args:
        audio_data: 会议录音
        meeting_info: 会议信息
        language: 语言
    """
    import os
    
    if meeting_info is None:
        meeting_info = {
            "title": "会议",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "participants": []
        }
    
    transcriber = MeetingTranscriber()
    
    print("📝 生成会议纪要")
    print(f"   会议: {meeting_info.get('title', '未命名会议')}")
    print(f"   日期: {meeting_info.get('date')}")
    
    # 1. 转录音频
    print("\n1️⃣ 转录会议录音...")
    transcript = transcriber.transcribe_meeting.remote(
        audio_data, language, meeting_info
    )
    
    # 2. 提取关键点
    print("2️⃣ 提取关键信息...")
    key_points = transcriber.extract_key_points.remote(transcript["full_text"])
    
    # 3. 生成会议纪要
    print("3️⃣ 生成结构化纪要...")
    
    minutes = {
        "title": meeting_info.get("title", "会议纪要"),
        "date": meeting_info.get("date"),
        "participants": meeting_info.get("participants", []),
        "duration_minutes": round(transcript["duration_minutes"], 1),
        "generated_at": datetime.now().isoformat(),
        
        "summary": {
            "total_segments": len(transcript["segments"]),
            "decisions_count": len(key_points["decisions"]),
            "action_items_count": len(key_points["action_items"]),
        },
        
        "content": {
            "full_transcript": transcript["full_text"],
            "timeline": transcript["segments"][:20],  # 只保留前20段用于预览
            "decisions": key_points["decisions"],
            "action_items": key_points["action_items"],
            "questions": key_points["questions"],
        }
    }
    
    # 4. 保存会议纪要
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = re.sub(r'[^\w\-]', '_', meeting_info.get("title", "meeting"))[:30]
    output_path = f"/output/{safe_title}_{timestamp}.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(minutes, f, ensure_ascii=False, indent=2)
    
    output_volume.commit()
    
    print(f"\n✅ 会议纪要生成完成")
    print(f"   时长: {minutes['duration_minutes']} 分钟")
    print(f"   决策: {minutes['summary']['decisions_count']} 项")
    print(f"   待办: {minutes['summary']['action_items_count']} 项")
    print(f"   保存: {output_path}")
    
    return minutes


@app.function(image=image)
@modal.web_endpoint(method="POST")
def meeting_minutes_api(audio: bytes, title: str = "会议", participants: str = ""):
    """
    会议纪要 API
    
    POST /meeting_minutes_api
    Content-Type: audio/wav
    Query params:
    - title: 会议标题
    - participants: 参会人（逗号分隔）
    """
    meeting_info = {
        "title": title,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "participants": [p.strip() for p in participants.split(",") if p.strip()]
    }
    
    minutes = generate_meeting_minutes.remote(audio, meeting_info)
    
    return {
        "status": "success",
        "meeting_title": minutes["title"],
        "duration_minutes": minutes["duration_minutes"],
        "decisions": minutes["content"]["decisions"],
        "action_items": minutes["content"]["action_items"]
    }


@app.local_entrypoint()
def main():
    """演示（需要提供音频文件）"""
    print("📝 会议纪要自动生成")
    print("=" * 50)
    print("\n使用方法:")
    print("modal run whisper_meeting_minutes.py")
    print("\n然后调用 API:")
    print("curl -X POST -H 'Content-Type: audio/wav' \\")
    print("     --data-binary @meeting.wav \\")
    print("     'https://your-app--meeting-minutes-api.modal.run?title=周会'")
    print("\n💡 提示:")
    print("1. 支持 mp3, wav, m4a 等格式")
    print("2. 会议纪要保存在 meeting-minutes Volume")
    print("3. 可对接 LLM 生成更智能的摘要")

