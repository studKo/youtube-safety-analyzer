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
        
        negative_sentences_count = sum(1 for s in sentiment_results if s.get('negative_score', 0) > 0.8)
        elapsed = round(time.time() - start_time, 2)

        db_url = os.path.basename(url_or_path) if is_uploaded_file else url_or_path
        
        transcription_obj = Transcription.objects.create(
            user=user,
            youtube_url=db_url,
            title=video_title,
            transcript=transcript,
            found_bad_words=found_words,
            bad_word_score=bad_score,
            sentiment_results=sentiment_results,
            negative_sentence_count=negative_sentences_count,
            elapsed_time=elapsed,
            model_name=model_used
        )

        if sentiment_results:
            for sentence_data in sentiment_results:
                VerifiedSentence.objects.create(
                    transcription=transcription_obj,
                    original_sentence=sentence_data.get('sentence', ''),
                    ai_negative_score=sentence_data.get('negative_score', 0)
                )

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