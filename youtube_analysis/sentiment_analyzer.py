# new/youtube_analysis/sentiment_analyzer.py

from transformers import pipeline
import kss
import re # 정규표현식 모듈

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

# [수정] 함수 시그니처 변경: text(문자열) -> text_segments(문자열 리스트)
def analyze_sentiment(text_segments, model_name="klue/roberta-large"):
    """
    [수정] Whisper 세그먼트 리스트를 받아, 각 세그먼트별로 감성 분석을 수행합니다.
    """
    classifier = sentiment_classifiers.get(model_name)
    if classifier is None:
        raise RuntimeError(f"{model_name} 모델이 초기화되지 않았습니다.")
    
    # [신규] 모든 세그먼트의 분석 결과를 담을 최종 리스트
    all_results = []
    
    if not text_segments:
        return []

    # [신규] text_segments 리스트(Whisper가 1차 분리)를 반복
    for segment_text in text_segments:
        if not segment_text.strip():
            continue # 빈 세그먼트 스킵
        
        # ▼▼▼▼▼ (이하 로직은 이전과 동일, 단 'text' -> 'segment_text'로 변경) ▼▼▼▼▼

        # 1. kss를 사용하여 '개별 세그먼트(segment_text)'를 2차 문장 분리
        try:
            original_sentences = kss.split_sentences(segment_text)
            original_sentences = [s.strip() for s in original_sentences if s.strip()]
        except Exception:
            # kss 오류 시 세그먼트 텍스트 통째로 사용
            original_sentences = [segment_text.strip()] 

        if not original_sentences:
            continue # 이 세그먼트에서 문장을 못 찾으면 다음 세그먼트로

        # 2. 감성 분석 모델을 위한 '한글 전용' 문장 리스트 생성
        sentences_for_analysis = []
        for s in original_sentences:
            korean_text = re.sub(r'[a-zA-Z]', '', s) # 영어 알파벳 제거
            korean_text = re.sub(r'[^가-힣0-9?.!]', ' ', korean_text) # 한글/숫자/구두점 외 제거
            korean_text = korean_text.strip()
            sentences_for_analysis.append(korean_text)

        # 3. '한글 전용' 리스트로 감성 분석 실행
        try:
            current_segment_scores = classifier(sentences_for_analysis)
        except Exception as e:
            print(f"❌ 감성 분석 중 오류 발생 (세그먼트 무시): {e}")
            # 이 세그먼트 분석에 실패하면, 점수 없이 원본 문장만 추가
            segment_results = [{"sentence": s, "negative_score": 0.0} for s in original_sentences]
            all_results.extend(segment_results)
            continue # 다음 세그먼트로

        # 4. 결과 조합 (원본 문장 + 분석 점수)
        segment_results = []
        for i, original_sentence in enumerate(original_sentences):
            scores = current_segment_scores[i]
            
            negative_score = next(
                (item['score'] for item in scores 
                 if item['label'].upper() == 'NEGATIVE' or item['label'] == 'LABEL_0'), 
                0.0 
            )
            
            segment_results.append({
                "sentence": original_sentence, # 원본 문장 (영어 포함)
                "negative_score": round(negative_score, 4)
            })
        
        # [신규] 이 세그먼트의 결과를 최종 리스트에 추가
        all_results.extend(segment_results)
    
    # [수정] 모든 세그먼트의 분석이 완료된 최종 리스트 반환
    return all_results