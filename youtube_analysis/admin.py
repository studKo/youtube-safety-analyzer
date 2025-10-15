# new/youtube_analysis/admin.py

from django.contrib import admin
from .models import Transcription, BadWord, UnverifiedTranscription, VerifiedSentence

class VerifiedSentenceInline(admin.TabularInline):
    """
    Transcription 상세 페이지 내에서 VerifiedSentence를 함께 보여주고 수정하기 위한 설정입니다.
    """
    model = VerifiedSentence
    fields = ('original_sentence', 'ai_negative_score', 'human_verification')
    readonly_fields = ('original_sentence', 'ai_negative_score')
    extra = 0

@admin.register(Transcription)
class TranscriptionAdmin(admin.ModelAdmin):
    """
    'Transcriptions'(전체 분석 기록) 메뉴에 대한 관리자 페이지 설정입니다.
    """
    list_display = ("title", "user", "bad_word_score", "negative_sentence_count", "is_verified", "created_at")
    list_filter = ("created_at", "model_name", "is_verified")
    list_editable = ("is_verified",)
    search_fields = ("youtube_url", "title", "user__username")
    ordering = ("-created_at",)
    inlines = [VerifiedSentenceInline]

@admin.register(BadWord)
class BadWordAdmin(admin.ModelAdmin):
    """
    '유해 단어 사전' 메뉴에 대한 관리자 페이지 설정입니다.
    """
    list_display = ('word', 'category', 'weight')
    search_fields = ('word',)
    list_filter = ('category',)
    ordering = ('-weight', 'word')

@admin.register(UnverifiedTranscription)
class UnverifiedTranscriptionAdmin(admin.ModelAdmin):
    """
    '검수 대기 목록' 메뉴에 대한 관리자 페이지 설정입니다.
    """
    list_display = ("title", "user", "bad_word_score", "negative_sentence_count", "created_at")
    ordering = ("-created_at",)
    inlines = [VerifiedSentenceInline]
    
    def get_queryset(self, request):
        """
        이 관리자 페이지에서는 is_verified=False인 데이터만 보여주도록 설정합니다.
        """
        return super().get_queryset(request).filter(is_verified=False)