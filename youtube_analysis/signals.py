# new/youtube_analysis/signals.py

import csv
import os
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import VerifiedSentence

@receiver(post_save, sender=VerifiedSentence)
def save_verified_sentence_to_csv(sender, instance, **kwargs):
    """
    VerifiedSentence 객체가 저장될 때마다, 검수된 데이터를 CSV 파일에 추가합니다.
    """
    # human_verification 필드가 비어있지 않은 경우 (즉, 관리자가 라벨링한 경우)에만 실행
    if instance.human_verification:
        # CSV 파일 경로 설정 (프로젝트 루트에 'verified_data.csv'로 저장)
        file_path = os.path.join(settings.BASE_DIR, 'verified_data.csv')
        
        # 파일이 존재하지 않으면 헤더를 추가
        file_exists = os.path.isfile(file_path)
        
        # CSV 파일에 데이터 추가 (append 모드)
        with open(file_path, 'a', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            
            if not file_exists:
                writer.writerow(['text', 'label']) # 헤더 작성
            
            # 데이터 작성: [원본 문장, 관리자 검수 결과]
            writer.writerow([instance.original_sentence, instance.human_verification])