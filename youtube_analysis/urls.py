# new/youtube_analysis/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # 기존 URL 패턴들
    path('api/analyze/', views.analyze_api, name='analyze_api'),
    path('detail/', views.detail_page, name='detail_page'),
    path('sentiment-detail/<int:transcription_id>/', views.sentiment_detail_view, name='sentiment_detail_page'),
    path('compare/', views.compare_page, name='compare_page'),
]