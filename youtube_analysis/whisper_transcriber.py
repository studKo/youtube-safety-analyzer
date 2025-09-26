# new/youtube_analysis/whisper_transcriber.py

import whisper
import torch
from django.apps import apps
from .sentiment_analyzer import analyze_sentiment

BAD_WORDS = [
    "시발", "새끼", "개새끼", "병신", "존나", "지랄", "미친", "미친년", "씨발", "씨발년", "개자식", "닥쳐", "등신", "좆", "씹",
    "좆까", "좆밥", "돌대가리", "쓰레기", "애미", "애비", "쌍놈", "년", "련", "또라이", "놈", "썅", "염병",
    "옘병", "닥치라", "꺼져", "꼰대", "개같은", "개가튼", "호로새끼", "씹새끼", "씨팔", "씨부랄", "씨댕",
    "씨바", "미친놈", "미친년", "똘추", "개놈", "개년", "씨방", "병맛", "게같은","게같은년",
    "개자식년", "개자슥", "개자슥년", "개같은년","연병",
    "썅놈", "썅년", "썅년이", "썅놈이", "좆만한", "개소리",
]

def transcribe_audio(audio_path):
    model = apps.get_app_config('youtube_analysis').model
    if model is None:
        raise RuntimeError("Whisper 모델이 로드되지 않았습니다.")

    try:
        result = model.transcribe(audio_path, fp16=torch.cuda.is_available()) # GPU 사용 시 fp16 활성화
        transcript = result.get("text", "").strip()
        
        bad_word_count = sum(transcript.lower().count(word) for word in BAD_WORDS)
        sentiment_results = analyze_sentiment(transcript)
        
        return transcript, bad_word_count, sentiment_results, "whisper-medium"

    except Exception as e:
        print("❌ 분석 중 예외 발생:", e)
        raise e