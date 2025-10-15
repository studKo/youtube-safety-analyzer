# new/youtube_analysis/sentiment_analyzer.py

from transformers import pipeline
import kss
import re # 정규표현식 모듈 추가

sentiment_classifiers = {}

def initialize_sentiment_analyzer():
    global sentiment_classifiers
    if not sentiment_classifiers:
        models_to_load = ["klue/roberta-large", "beomi/kcbert-large"]
        for model_name in models_to_load:
            print(f"✅ 감성 분석 모델 ({model_name}) 로드를 시작합니다...")
            try:
                sentiment_classifiers[model_name] = pipeline(
                    "sentiment-analysis", 
                    model=model_name,
                    top_k=None
                )
                print(f"✅ {model_name} 모델 로드 완료")
            except Exception as e:
                print(f"❌ {model_name} 모델 로드 실패: {e}")

def analyze_sentiment(text, model_name="klue/roberta-large"):
    """
    지정된 모델을 사용하여 감성 분석을 수행합니다.
    (내부적으로 한글만 필터링하여 분석합니다.)
    """
    classifier = sentiment_classifiers.get(model_name)
    if classifier is None:
        raise RuntimeError(f"{model_name} 모델이 초기화되지 않았습니다.")

    try:
        # ▼▼▼▼▼▼ 감성 분석 전, 한글만 남기는 전처리 로직 강화 ▼▼▼▼▼▼
        # 1. 영어 알파벳 제거
        korean_text_only = re.sub(r'[a-zA-Z]', '', text)
        # 2. 한글, 숫자, 기본 구두점을 제외한 모든 문자 공백으로 변환
        korean_text_only = re.sub(r'[^가-힣0-9?.!]', ' ', korean_text_only)

        # 3. kss를 사용하여 문장 분리
        sentences = kss.split_sentences(korean_text_only)
        
        # 4. 비어있는 문장 최종 제거
        sentences = [s.strip() for s in sentences if s.strip()]
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

        if not sentences:
            return []
            
    except Exception:
        sentences = [text] # 오류 발생 시 원본 텍스트 사용

    all_scores = classifier(sentences)
    
    results = []
    for i, sentence in enumerate(sentences):
        scores = all_scores[i]
        negative_score = next((item['score'] for item in scores if item['label'].upper() == 'NEGATIVE' or item['label'] == 'LABEL_0'), 0)
        
        results.append({
            "sentence": sentence,
            "negative_score": round(negative_score, 4)
        })
        
    return results