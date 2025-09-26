# new/youtube_analysis/models.py

from django.db import models

class Transcription(models.Model):
    youtube_url = models.URLField(unique=True)
    title = models.CharField(max_length=255)
    transcript = models.TextField(blank=True)
    bad_word_count = models.IntegerField(default=0)
    
    # 감성 분석 결과를 저장할 필드 추가
    sentiment_results = models.JSONField(null=True, blank=True)
    negative_sentence_count = models.IntegerField(default=0)

    elapsed_time = models.FloatField(default=0.0)
    model_name = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title