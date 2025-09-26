from django.urls import path
from . import views

urlpatterns = [
    path('', views.youtube_page, name='youtube_page'),
    path('api/analyze/', views.analyze_badwords, name='analyze_badwords'),
    path('api/video_analyze/', views.analyze_video_frames, name='analyze_video_frames'),
    path('api/analyze_all/', views.analyze_all, name='analyze_all'),
    path('result/rating/', views.rating_only_page, name='rating_only_page'),
    path('result/detail/', views.detail_page, name='detail_page'),
    path('detail/', views.detail_page),
]