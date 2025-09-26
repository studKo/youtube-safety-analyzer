# new/youtube_analysis/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.youtube_page, name='youtube_analysis'),
    path('detail/', views.detail_page, name='detail_page'),
    path('api/analyze/', views.analyze_api, name='analyze_api'),
    path('sentiment/<int:transcription_id>/', views.sentiment_detail_view, name='sentiment_detail_page'),
]