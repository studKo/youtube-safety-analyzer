# new/youtube_analysis/services.py

import time
import os
from django.conf import settings
from .models import Transcription, VerifiedSentence
from .whisper_transcriber import transcribe_audio
from video_downloader.downloader import download_audio_from_youtube, AgeRestrictedError
from yt_dlp.utils import DownloadError

class AnalysisError(Exception):
    pass

def run_analysis_pipeline(user, url_or_path, sentiment_model, is_uploaded_file=False, original_filepath=None):
    audio_path = None
    try:
        start_time = time.time()
        audio_path, video_title = download_audio_from_youtube(url_or_path, output_dir=settings.MEDIA_ROOT)
        
        transcript, found_words, bad_score, sentiment_results, model_used = transcribe_audio(audio_path, sentiment_model_name=sentiment_model)
        
        # --- [수정 1] 긍정, 부정, 중립 문장 수 계산 로직 확장 ---
        # 3가지 카운트를 모두 0으로 초기화
        positive_sentences_count = 0
        negative_sentences_count = 0
        neutral_sentences_count = 0

        if sentiment_results:
            for s in sentiment_results:
                pos_score = s.get('positive_score', 0)
                neg_score = s.get('negative_score', 0)
                
                # 기존 로직(views.py의 get_grade)과의 일관성을 위해 0.8 임계값 사용
                if neg_score > 0.6:
                    negative_sentences_count += 1
                # 긍정 임계값 (로직 일관성을 위해 0.8 설정, 필요시 이 값을 조정)
                elif pos_score > 0.:
                    positive_sentences_count += 1
                # 긍정, 부정이 모두 0.8 미만이면 중립으로 간주
                else:
                    neutral_sentences_count += 1
        # --------------------------------------------------------

        elapsed = round(time.time() - start_time, 2)

        db_url = os.path.basename(url_or_path) if is_uploaded_file else url_or_path
        
        # --- [수정 2] Transcription 객체 생성 시 모든 집계 값 저장 ---
        transcription_obj = Transcription.objects.create(
            user=user,
            youtube_url=db_url,
            title=video_title,
            transcript=transcript,
            found_bad_words=found_words,
            bad_word_score=bad_score,
            sentiment_results=sentiment_results,
            
            # 3가지 카운트 모두 저장
            positive_sentence_count=positive_sentences_count,
            negative_sentence_count=negative_sentences_count,
            neutral_sentence_count=neutral_sentences_count,
            
            elapsed_time=elapsed,
            model_name=model_used
        )
        # ----------------------------------------------------------

        if sentiment_results:
            # --- [수정 3] VerifiedSentence 객체 생성 시 모든 확률 값 저장 ---
            for sentence_data in sentiment_results:
                VerifiedSentence.objects.create(
                    transcription=transcription_obj,
                    original_sentence=sentence_data.get('sentence', ''),
                    
                    # 3가지 점수 모두 저장
                    ai_positive_score=sentence_data.get('positive_score', 0),
                    ai_negative_score=sentence_data.get('negative_score', 0),
                    ai_neutral_score=sentence_data.get('neutral_score', 0)
                )
            # ------------------------------------------------------------

    except AgeRestrictedError as e:
        raise e
    except (DownloadError, FileNotFoundError):
        raise AnalysisError("영상/파일을 처리하는 중 오류가 발생했습니다. URL이나 파일을 다시 확인해주세요.")
    except Exception as e:
        print(f"❌ 알 수 없는 오류 발생: {e}")
        raise AnalysisError(f"분석 중 알 수 없는 오류가 발생했습니다: {e}")
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        if is_uploaded_file and original_filepath and os.path.exists(original_filepath):
            os.remove(original_filepath)