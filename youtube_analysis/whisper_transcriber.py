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
    (수정) Whisper 'segments'를 활용하여 문장 분리 정확도 향상
    """
    model = apps.get_app_config('youtube_analysis').model
    if model is None:
        raise RuntimeError("Whisper 모델이 로드되지 않았습니다.")

    try:
        # 1. 음성-텍스트 변환 (수정: 'segments'도 가져옴)
        result = model.transcribe(audio_path, fp16=torch.cuda.is_available())
        
        # [유지] 'transcript'는 DB의 '전체 본문' 저장을 위해 유지
        transcript = result.get("text", "").strip() 
        
        # [신규] Whisper가 분리한 '세그먼트 리스트'를 가져옴
        segments = result.get("segments", [])
        
        transcript_lower = transcript.lower()

        # 2. DB에서 유해 단어 정보 가져오기 (전체 텍스트 기준 - 변경 없음)
        bad_words_from_db = BadWord.objects.all()
        found_words_details = {}
        total_score = 0
        words_in_transcript = re.findall(r'\b\w+\b', transcript_lower)
        word_counts = Counter(words_in_transcript)

        for bad_word in bad_words_from_db:
            word = bad_word.word.lower()
            if word_counts[word] > 0:
                count = word_counts[word]
                found_words_details[bad_word.word] = {
                    'count': count,
                    'category': bad_word.get_category_display(), 
                    'weight': bad_word.weight
                }
                total_score += count * bad_word.weight
        
        # 4. [수정] 감성 분석 수행:
        #    전체 텍스트(transcript) 대신, '세그먼트 리스트'에서 추출한 텍스트 리스트를 전달
        
        # 세그먼트에서 텍스트('text')만 추출한 리스트를 생성
        segment_texts = [s['text'].strip() for s in segments if s.get('text')]
        
        # 'segment_texts' 리스트를 통째로 분석기에 전달
        sentiment_results = analyze_sentiment(segment_texts, model_name=sentiment_model_name)
        
        whisper_model_name = "whisper-medium"
        full_model_name = f"{whisper_model_name} + {sentiment_model_name}"
        
        # 5. 상세 결과 반환
        # (transcript는 전체 본문, sentiment_results는 세그먼트 기반으로 분리된 문장 목록)
        return transcript, found_words_details, total_score, sentiment_results, full_model_name

    except Exception as e:
        print(f"❌ 분석 중 예외 발생: {e}")
        raise e