# new/youtube_analysis/models.py

from django.db import models
from django.conf import settings

class BadWord(models.Model):
    CATEGORY_CHOICES = [
        ('profanity', '욕설/비속어'),
        ('hate_speech', '혐오 발언'),
        ('discrimination', '차별적 발언'),
        ('violence', '폭력적/선정적 표현'),
    ]
    word = models.CharField(max_length=100, unique=True, verbose_name='유해 단어')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='profanity', verbose_name='종류')
    weight = models.IntegerField(default=1, verbose_name='가중치 (높을수록 심각)')
    def __str__(self):
        return self.word
    class Meta:
        verbose_name = '유해 단어'
        verbose_name_plural = '유해 단어 사전'

class Transcription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    youtube_url = models.CharField(max_length=500)
    title = models.CharField(max_length=255)
    transcript = models.TextField(blank=True)
    found_bad_words = models.JSONField(null=True, blank=True, default=dict)
    bad_word_score = models.IntegerField(default=0, verbose_name='유해 단어 점수')
    sentiment_results = models.JSONField(null=True, blank=True)
    negative_sentence_count = models.IntegerField(default=0)
    elapsed_time = models.FloatField(default=0.0)
    model_name = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False, verbose_name='관리자 검수 완료')
    def __str__(self):
        return self.title

class UnverifiedTranscription(Transcription):
    """
    검수가 필요한(is_verified=False) 분석 결과만 따로 보여주기 위한 Proxy 모델입니다.
    """
    class Meta:
        proxy = True
        verbose_name = '검수 대기 분석'
        verbose_name_plural = '검수 대기 목록'

class VerifiedSentence(models.Model):
    """
    AI가 분석한 각 문장에 대해 관리자가 검수한 결과를 저장하는 모델입니다.
    """
    SENTIMENT_CHOICES = [
        ('positive', '긍정'),
        ('negative', '부정'),
        ('neutral', '중립'),
    ]
    
    transcription = models.ForeignKey(Transcription, on_delete=models.CASCADE, related_name='verified_sentences')
    original_sentence = models.TextField(verbose_name='원본 문장')
    ai_negative_score = models.FloatField(default=0.0, verbose_name='AI 부정 확률')
    
    human_verification = models.CharField(
        max_length=10, 
        choices=SENTIMENT_CHOICES, 
        blank=True, 
        null=True, 
        verbose_name='관리자 검수 결과'
    )

    class Meta:
        verbose_name = '검수 완료 문장'
        verbose_name_plural = '검수 완료 문장들'