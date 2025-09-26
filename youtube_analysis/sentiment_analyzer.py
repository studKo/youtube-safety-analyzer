# new/youtube_analysis/sentiment_analyzer.py

from transformers import pipeline
import kss

sentiment_classifier = None

def initialize_sentiment_analyzer():
    """
    Django 앱 시작 시 감성 분석 모델을 한 번만 로드합니다.
    """
    global sentiment_classifier
    if sentiment_classifier is None:
        print("✅ 감성 분석 전문 모델(klue/roberta-large) 로드를 시작합니다...")
        
        sentiment_classifier = pipeline(
            "sentiment-analysis", 
            model="klue/roberta-large",
            top_k=None
        )
        print("✅ 감성 분석 모델 로드 완료")

def analyze_sentiment(text):
    """
    전체 텍스트를 문장 단위로 나누고, 모든 문장을 한 번에 감성 분석합니다. (배치 처리)
    """
    if sentiment_classifier is None:
        raise RuntimeError("감성 분석 모델이 초기화되지 않았습니다.")

    try:
        # 문장 분리
        sentences = [s.strip() for s in text.replace('?', '.').replace('!', '.').split('.') if s.strip()]
        if not sentences:
            return []
    except Exception:
        sentences = [text]

    # 문장 리스트 전체를 모델에 한 번에 전달하여 분석 속도 향상
    all_scores = sentiment_classifier(sentences)
    
    results = []
    # 분석된 결과와 원래 문장을 짝지어 최종 결과 리스트 생성
    for i, sentence in enumerate(sentences):
        scores = all_scores[i]
        negative_score = next((item['score'] for item in scores if item['label'].upper() == 'NEGATIVE' or item['label'] == 'LABEL_0'), 0)
        
        results.append({
            "sentence": sentence,
            "negative_score": round(negative_score, 4)
        })
        
    return results