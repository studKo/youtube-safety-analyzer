# new/youtube_analysis/whisper_transcriber.py

import whisper
import torch
from django.apps import apps
from .sentiment_analyzer import analyze_sentiment
from .models import BadWord # DB에서 유해 단어를 가져오기 위해 추가
import re
from collections import Counter

def transcribe_audio(audio_path, sentiment_model_name):
    """
    오디오 파일을 분석하여 텍스트, 유해 단어 정보, 감성 분석 결과를 반환합니다.
    """
    model = apps.get_app_config('youtube_analysis').model
    if model is None:
        raise RuntimeError("Whisper 모델이 로드되지 않았습니다.")

    try:
        # 1. 음성-텍스트 변환
        result = model.transcribe(audio_path, fp16=torch.cuda.is_available())
        transcript = result.get("text", "").strip()
        transcript_lower = transcript.lower()

        # 2. DB에서 모든 유해 단어 정보 가져오기
        bad_words_from_db = BadWord.objects.all()
        
        # 3. 유해 단어 검출 및 상세 정보 계산
        found_words_details = {}
        total_score = 0
        
        # 텍스트를 단어 단위로 분리 (정규표현식 사용)
        words_in_transcript = re.findall(r'\b\w+\b', transcript_lower)
        word_counts = Counter(words_in_transcript)

        for bad_word in bad_words_from_db:
            word = bad_word.word.lower()
            # Counter를 사용하여 단어의 등장 횟수를 효율적으로 계산
            if word_counts[word] > 0:
                count = word_counts[word]
                found_words_details[bad_word.word] = {
                    'count': count,
                    'category': bad_word.get_category_display(), # 'profanity' -> '욕설/비속어'
                    'weight': bad_word.weight
                }
                total_score += count * bad_word.weight
        
        # 4. 감성 분석 수행 (이 부분은 변경 없음)
        sentiment_results = analyze_sentiment(transcript, model_name=sentiment_model_name)
        
        whisper_model_name = "whisper-medium"
        full_model_name = f"{whisper_model_name} + {sentiment_model_name}"
        
        # 5. 상세 결과 반환
        return transcript, found_words_details, total_score, sentiment_results, full_model_name

    except Exception as e:
        print(f"❌ 분석 중 예외 발생: {e}")
        raise e