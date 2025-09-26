from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from youtube_analysis.whisper_transcriber import transcribe_audio, BAD_WORDS
from youtube_analysis.models import Transcription
import os
import time
from django.conf import settings
from django.shortcuts import render
from video_downloader.downloader import download_audio_from_youtube


def transcribe_async_page(request):
    return render(request, "transcribe_async.html")

@csrf_exempt
def transcribe_api(request):
    if request.method == "POST":
        youtube_url = request.POST.get("url")

        if not youtube_url:
            return JsonResponse({"status": "error", "message": "URL이 없습니다."}, status=400)

        try:
            saved = Transcription.objects.get(youtube_url=youtube_url)
            return JsonResponse({
                "status": "success",
                "transcript": saved.transcript,
                "title": saved.title,
                "elapsed": saved.elapsed_time,
                "bad_word_count": saved.bad_word_count,
                "cached": True,
            })
        except Transcription.DoesNotExist:
            pass

        try:
            start = time.time()
            audio_path, video_title = download_audio_from_youtube(youtube_url, output_dir=settings.MEDIA_ROOT)

            print(" 다운로드 완료:", audio_path)

            if not os.path.exists(audio_path):
                return JsonResponse({"status": "error", "message": "오디오 파일 없음"}, status=500)

            transcript, bad_word_count, used_model = transcribe_audio(audio_path)
            elapsed = round(time.time() - start, 2)

            print(" 자막 일부:", transcript[:80])
            print(" 유해어 수:", bad_word_count)

            if not transcript.strip():
                return JsonResponse({
                    "status": "error",
                    "message": "자막이 감지되지 않았습니다. (무음 또는 짧은 영상)"
                }, status=500)

            saved = Transcription.objects.create(
                youtube_url=youtube_url,
                title=video_title,
                transcript=transcript,
                bad_word_count=bad_word_count,
                elapsed_time=elapsed,
                model_name=used_model
            )

            try:
                os.remove(audio_path)
            except Exception as e:
                print("⚠️ mp3 삭제 실패 (무시):", e)

            return JsonResponse({
                "status": "success",
                "transcript": transcript,
                "title": video_title,
                "elapsed": elapsed,
                "bad_word_count": bad_word_count,
                "cached": False,
            })

        except Exception as e:
            print("❌ 예외 발생:", e)
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "POST만 지원됩니다."}, status=405)

print("유해어 리스트:", BAD_WORDS)