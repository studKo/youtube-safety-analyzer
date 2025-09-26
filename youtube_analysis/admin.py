from django.contrib import admin
from django.contrib.admin.actions import delete_selected
from .models import Transcription

@admin.register(Transcription)
class TranscriptionAdmin(admin.ModelAdmin):
    list_display = ("title", "youtube_url", "short_transcript", "created_at", "elapsed_time")
    search_fields = ("youtube_url", "title")
    ordering = ("-created_at",)
    actions = [delete_selected]

    def short_transcript(self, obj):
        return obj.transcript[:50] + "..." if len(obj.transcript) > 50 else obj.transcript

    short_transcript.short_description = "자막 요약"

    def has_delete_permission(self, request, obj=None):
        return True