# new/youtube_analysis/views.py

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.urls import reverse
from urllib.parse import quote
import json
import os
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage

from .services import run_analysis_pipeline, AnalysisError
from .models import Transcription
from video_downloader.downloader import AgeRestrictedError

def get_grade(bad_word_score, negative_sentences_count):
    """
    유해성 점수와 부정 문장 수를 기반으로 영상 등급을 결정합니다.
    """
    harmful_score = (bad_word_score * 2) + negative_sentences_count
    if harmful_score >= 20: return "19세 이용가", "연령고지19세.png"
    if harmful_score >= 15: return "15세 이용가", "연령고지15세.png"
    if harmful_score >= 10: return "12세 이용가", "연령고지12세.png"
    return "7세 이용가", "연령고지7세.png"

def youtube_page(request):
    """
    메인 분석 요청 페이지를 렌더링합니다.
    """
    return render(request, "youtube.html")

def detail_page(request):
    """
    분석 결과를 상세하게 보여주는 페이지를 렌더링합니다.
    """
    url_or_path = request.GET.get("url")
    if not url_or_path:
        return render(request, "detail.html", {"error_message": "URL 또는 파일 경로가 없습니다."})
    
    try:
        result = Transcription.objects.filter(youtube_url=url_or_path).latest('created_at')
        grade_text, grade_image = get_grade(result.bad_word_score, result.negative_sentence_count)
        
        bad_words_list = list(result.found_bad_words.keys()) if result.found_bad_words else []

        analysis_result = {
            'id': result.id,
            'title': result.title,
            'youtube_url': result.youtube_url,
            'transcript': result.transcript,
            'elapsed_time': result.elapsed_time,
            'model_name': result.model_name,
            'grade_text': grade_text,
            'grade_image_path': f"/static/images/{grade_image}",
            'bad_word_score': result.bad_word_score,
            'negative_sentence_count': result.negative_sentence_count,
            'sentiment_results': result.sentiment_results,
            'found_bad_words': result.found_bad_words,
            'bad_words_json': json.dumps(bad_words_list)
        }

        high_negative_sentences = []
        if result.sentiment_results:
            for sentence_data in result.sentiment_results:
                if sentence_data.get('negative_score', 0) > 0.6:
                    sentence_data['negative_percentage'] = int(sentence_data['negative_score'] * 100)
                    high_negative_sentences.append(sentence_data)
        analysis_result['high_negative_sentences'] = high_negative_sentences
        
        return render(request, "detail.html", {'analysis_result': analysis_result})
        
    except Transcription.DoesNotExist:
        return render(request, "detail.html", {"error_message": "아직 분석되지 않은 자료입니다."})
    except Exception as e:
        return render(request, "detail.html", {"error_message": f"오류 발생: {e}"})

@csrf_exempt
@login_required
def analyze_api(request):
    """
    AJAX 요청을 받아 분석 파이프라인을 실행하는 API 뷰입니다.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "POST 요청만 가능합니다."}, status=405)
    
    url_or_path = None
    is_uploaded_file = False
    original_filepath = None
    
    if 'video_file' in request.FILES:
        uploaded_file = request.FILES['video_file']
        sentiment_model = request.POST.get("sentiment_model", "klue/roberta-large")
        file_name = default_storage.save(uploaded_file.name, uploaded_file)
        url_or_path = os.path.join(settings.MEDIA_ROOT, file_name)
        original_filepath = url_or_path
        is_uploaded_file = True
    else:
        try:
            data = json.loads(request.body)
            url_or_path = data.get("url")
            sentiment_model = data.get("sentiment_model", "klue/roberta-large")
            if not url_or_path:
                return JsonResponse({"status": "error", "message": "URL 또는 파일을 입력해주세요."}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "요청 형식이 잘못되었습니다."}, status=400)

    db_identifier = os.path.basename(url_or_path) if is_uploaded_file else url_or_path

    try:
        existing_result = Transcription.objects.filter(
            user=request.user, 
            youtube_url=db_identifier,
            model_name__icontains=sentiment_model
        ).latest('created_at')
        
        if timezone.now() - existing_result.created_at <= timedelta(hours=48):
            redirect_url = f"{reverse('detail_page')}?url={quote(db_identifier)}"
            return JsonResponse({"status": "success", "redirect_url": redirect_url})
    except Transcription.DoesNotExist:
        pass

    try:
        run_analysis_pipeline(request.user, url_or_path, sentiment_model, is_uploaded_file, original_filepath)
    except AgeRestrictedError as e:
        return JsonResponse({"status": "age_restricted", "message": str(e)}, status=200)
    except AnalysisError as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

    redirect_url = f"{reverse('detail_page')}?url={quote(db_identifier)}"
    return JsonResponse({"status": "success", "redirect_url": redirect_url})

@login_required
def compare_page(request):
    """
    두 모델의 분석 결과를 나란히 비교하여 보여주는 페이지를 렌더링합니다.
    """
    kcbert_id = request.GET.get('kcbert_id')
    roberta_id = request.GET.get('roberta_id')

    if not kcbert_id or not roberta_id:
        return render(request, "compare_detail.html", {"error_message": "비교할 분석 기록이 올바르지 않습니다."})
    
    try:
        # 현재 로그인한 사용자의 분석 기록 중에서만 찾아옵니다. (보안 강화)
        kcbert_result = get_object_or_404(Transcription, id=kcbert_id, user=request.user)
        roberta_result = get_object_or_404(Transcription, id=roberta_id, user=request.user)

        # KcBERT 등급 계산
        kc_grade_text, _ = get_grade(kcbert_result.bad_word_score, kcbert_result.negative_sentence_count)
        kcbert_result.grade_text = kc_grade_text

        # RoBERTa 등급 계산
        ro_grade_text, _ = get_grade(roberta_result.bad_word_score, roberta_result.negative_sentence_count)
        roberta_result.grade_text = ro_grade_text

        context = {
            'kcbert_result': kcbert_result,
            'roberta_result': roberta_result,
            'title': kcbert_result.title,
        }
        return render(request, "compare_detail.html", context)
    except Transcription.DoesNotExist:
        return render(request, "compare_detail.html", {"error_message": "분석 기록을 찾을 수 없습니다."})

def sentiment_detail_view(request, transcription_id):
    """
    전체 문장에 대한 감성 분석 결과를 상세히 보여주는 페이지입니다.
    """
    transcription = get_object_or_404(Transcription, pk=transcription_id)
    if transcription.sentiment_results:
        for item in transcription.sentiment_results:
            percentage = int(item.get('negative_score', 0) * 100)
            item['negative_percentage'] = percentage
            if percentage > 80: item['bar_class'] = 'sentiment-bar-red'
            elif percentage > 50: item['bar_class'] = 'sentiment-bar-yellow'
            else: item['bar_class'] = 'sentiment-bar-green'
    context = {'analysis_result': transcription}
    return render(request, "sentiment_detail.html", context)