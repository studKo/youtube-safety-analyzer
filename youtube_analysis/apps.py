# new/youtube_analysis/apps.py

from django.apps import AppConfig
import os
import whisper
from .sentiment_analyzer import initialize_sentiment_analyzer

class YoutubeAnalysisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'youtube_analysis'
    model = None

    def ready(self):
        if os.environ.get('RUN_MAIN'):
            print("✅ AppConfig에서 모델 로드를 시작합니다...")
            
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            if device == "cuda":
                print("✅ [성공] NVIDIA GPU('cuda') 감지. GPU를 사용하여 모델을 로드합니다.")
            else:
                print("⚠️ [경고] NVIDIA GPU('cuda')를 찾을 수 없습니다. CPU를 사용하여 모델을 로드합니다. (속도 저하)")

            try:
                # 시연을 위해 "base" 모델 사용, 실제 운영 시 "medium"으로 변경 권장
                self.model = whisper.load_model("base", device=device)
                print(f"✅ Whisper '{device}' 모델 로드 완료")
                
                initialize_sentiment_analyzer()
                
            except Exception as e:
                print(f"❌ 모델 로드 실패: {e}")
                self.model = None

        import youtube_analysis.signals
