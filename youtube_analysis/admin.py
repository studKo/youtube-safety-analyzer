# new/youtube_analysis/admin.py

from django.contrib import admin
from .models import BadWord, Transcription, UnverifiedTranscription, VerifiedSentence

@admin.register(BadWord)
class BadWordAdmin(admin.ModelAdmin):
    """
    유해 단어 사전(BadWord) 관리자 설정
    """
    list_display = ('word', 'category', 'weight')
    search_fields = ('word',)
    list_filter = ('category',)


# --- [수정 1] 문장 검수를 위한 'Inline' 클래스 생성 ---
class VerifiedSentenceInline(admin.TabularInline):
    """
    Transcription(영상) 상세 페이지에서
    관련된 VerifiedSentence(문장)들을
    테이블 형태로 보여주기 위한 인라인 설정입니다.
    """
    model = VerifiedSentence
    
    # 인라인 테이블에 표시할 필드
    # 'human_verification'만 수정 가능하게 설정됩니다.
    fields = (
        'original_sentence', 
        'ai_positive_score', 
        'ai_negative_score', 
        'ai_neutral_score', 
        'human_verification'
    )
    
    # AI가 분석한 원본 문장과 점수는 수정하면 안 되므로 '읽기 전용'으로 설정
    readonly_fields = (
        'original_sentence', 
        'ai_positive_score', 
        'ai_negative_score', 
        'ai_neutral_score'
    )
    
    extra = 0 # 추가 빈칸 생성 안 함
    can_delete = False # 인라인에서 문장 삭제 금지

@admin.register(Transcription)
class TranscriptionAdmin(admin.ModelAdmin):
    """
    전체 분석 결과(Transcription) 관리자 설정
    """
    list_display = (
        'title', 
        'user', 
        'model_name', 
        'bad_word_score', 
        'negative_sentence_count', 
        'is_verified',  # 검수 완료 여부 표시
        'created_at'
    )
    search_fields = ('title', 'youtube_url', 'transcript')
    list_filter = ('is_verified', 'model_name', 'created_at', 'user')
    
    # --- [수정 2] 'is_verified' 필드를 readonly에서 제거 ---
    # 관리자가 '검수 완료' 체크를 할 수 있어야 하므로 읽기 전용에서 제외합니다.
    readonly_fields = (
        'user', 'youtube_url', 'title', 'transcript',
        'found_bad_words', 'bad_word_score', 'sentiment_results',
        'positive_sentence_count', 'negative_sentence_count', 'neutral_sentence_count',
        'elapsed_time', 'model_name', 'created_at'
    )

    # --- [수정 3] 위에서 정의한 문장 인라인(Inline)을 여기에 추가 ---
    inlines = [VerifiedSentenceInline]


@admin.register(UnverifiedTranscription)
class UnverifiedTranscriptionAdmin(TranscriptionAdmin):
    """
    검수 대기 목록(Proxy Model) 관리자 설정
    - 부모인 TranscriptionAdmin의 설정을 그대로 상속받습니다.
    - 따라서 'inlines' 기능도 자동으로 포함됩니다.
    """
    
    def get_queryset(self, request):
        # is_verified=False 인 것만 필터링
        return super().get_queryset(request).filter(is_verified=False)
