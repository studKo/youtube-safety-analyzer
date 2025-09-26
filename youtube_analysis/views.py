# new/youtube_analysis/views.py

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.urls import reverse
from urllib.parse import quote
import json
import time
import os

from .whisper_transcriber import transcribe_audio, BAD_WORDS
from .models import Transcription
from video_downloader.downloader import download_audio_from_youtube, AgeRestrictedError

def get_grade(bad_word_count, negative_sentences_count):
    harmful_score = (bad_word_count * 2) + negative_sentences_count
    if harmful_score >= 20:
        return "19세 이용가", "연령고지19세.png"
    if harmful_score >= 15:
        return "15세 이용가", "연령고지15세.png"
    if harmful_score >= 10:
        return "12세 이용가", "연령고지12세.png"
    return "7세 이용가", "연령고지7세.png"

def youtube_page(request):
    return render(request, "youtube.html")

def detail_page(request):
    youtube_url = request.GET.get("url")
    if not youtube_url:
        return render(request, "detail.html", {"error_message": "URL이 없습니다."})
    try:
        result = Transcription.objects.get(youtube_url=youtube_url)
        grade_text, grade_image = get_grade(result.bad_word_count, result.negative_sentence_count)
        result.grade_text = grade_text
        result.grade_image_path = f"/static/images/{grade_image}"
        transcript_lower = result.transcript.lower()
        result.found_bad_words = list(set([word for word in BAD_WORDS if word in transcript_lower]))
        high_negative_sentences = []
        if result.sentiment_results:
            for sentence_data in result.sentiment_results:
                if sentence_data.get('negative_score', 0) > 0.8:
                    sentence_data['negative_percentage'] = int(sentence_data['negative_score'] * 100)
                    high_negative_sentences.append(sentence_data)
        result.high_negative_sentences = high_negative_sentences
        return render(request, "detail.html", {'analysis_result': result})
    except Transcription.DoesNotExist:
        return render(request, "detail.html", {"error_message": "아직 분석되지 않은 URL입니다."})
    except Exception as e:
        return render(request, "detail.html", {"error_message": f"오류 발생: {e}"})

@csrf_exempt
def analyze_api(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "POST 요청만 가능합니다."}, status=405)
    try:
        data = json.loads(request.body)
        youtube_url = data.get("url")
        if not youtube_url:
            return JsonResponse({"status": "error", "message": "URL을 입력해주세요."}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "요청 형식이 잘못되었습니다."}, status=400)

    try:
        Transcription.objects.get(youtube_url=youtube_url)
    except Transcription.DoesNotExist:
        try:
            start_time = time.time()
            audio_path, video_title = download_audio_from_youtube(youtube_url, output_dir=settings.MEDIA_ROOT)
            transcript, bad_word_count, sentiment_results, model_used = transcribe_audio(audio_path)
            negative_sentences_count = sum(1 for s in sentiment_results if s['negative_score'] > 0.8)
            elapsed = round(time.time() - start_time, 2)
            Transcription.objects.create(
                youtube_url=youtube_url,
                title=video_title,
                transcript=transcript,
                bad_word_count=bad_word_count,
                sentiment_results=sentiment_results,
                negative_sentence_count=negative_sentences_count,
                elapsed_time=elapsed,
                model_name=model_used
            )
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except AgeRestrictedError as e:
            return JsonResponse({"status": "age_restricted", "message": str(e)}, status=200)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    redirect_url = f"{reverse('detail_page')}?url={quote(youtube_url)}"
    return JsonResponse({"status": "success", "redirect_url": redirect_url})

def sentiment_detail_view(request, transcription_id):
    transcription = get_object_or_404(Transcription, pk=transcription_id)
    
    #  뷰에서 미리 CSS 클래스 이름까지 모두 계산
    if transcription.sentiment_results:
        for item in transcription.sentiment_results:
            percentage = int(item.get('negative_score', 0) * 100)
            item['negative_percentage'] = percentage
            
            # 퍼센트에 따라 CSS 클래스 이름을 결정하여 딕셔너리에 추가
            if percentage > 80:
                item['bar_class'] = 'sentiment-bar-red'
            elif percentage > 50:
                item['bar_class'] = 'sentiment-bar-yellow'
            else:
                item['bar_class'] = 'sentiment-bar-green'
            
    context = {
        'analysis_result': transcription
    }
    
    return render(request, "sentiment_detail.html", context)
