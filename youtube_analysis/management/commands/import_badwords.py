# youtube_analysis/management/commands/import_badwords.py

import os
from django.core.management.base import BaseCommand
from django.conf import settings
from youtube_analysis.models import BadWord

class Command(BaseCommand):
    """
    종류별로 분리된 유해 단어 .txt 파일들을 읽어와 데이터베이스에 자동으로 저장합니다.
    사용법: python manage.py import_badwords
    """
    help = '종류별 유해 단어 사전을 데이터베이스에 자동으로 등록합니다.'

    def handle(self, *args, **options):
        """
        명령어가 실행될 때 호출되는 메인 로직입니다.
        """
        # 처리할 파일 목록: (파일명, DB에 저장될 카테고리명, 기본 가중치)
        # BadWord 모델의 CATEGORY_CHOICES에 정의된 key값과 일치해야 합니다.
        files_to_import = [
            ('badwords_profanity.txt', 'profanity', 2),
            ('badwords_hate_speech.txt', 'hate_speech', 5),
            ('badwords_discrimination.txt', 'discrimination', 5),
            ('badwords_violence.txt', 'violence', 4),
        ]

        self.stdout.write(self.style.SUCCESS("유해 단어 자동 등록을 시작합니다..."))
        total_created_count = 0

        # 데이터베이스의 모든 유해 단어를 한번에 삭제 (초기화)
        # 이 줄을 주석 해제하면, 명령어를 실행할 때마다 기존 단어가 모두 지워지고 새로 등록됩니다.
        # BadWord.objects.all().delete()
        # self.stdout.write(self.style.WARNING("기존의 모든 유해 단어를 삭제했습니다."))

        for filename, category, weight in files_to_import:
            file_path = os.path.join(settings.BASE_DIR, filename)
            
            if not os.path.exists(file_path):
                self.stdout.write(self.style.WARNING(f"'{filename}' 파일을 찾을 수 없어 건너뜁니다."))
                continue

            with open(file_path, 'r', encoding='utf-8') as f:
                created_count_for_file = 0
                for line in f:
                    word = line.strip().lower()
                    if word:
                        # get_or_create: 단어가 이미 존재하면 건너뛰고, 없으면 새로 생성합니다. (중복 방지)
                        _, created = BadWord.objects.get_or_create(
                            word=word,
                            defaults={
                                'category': category,
                                'weight': weight,
                            }
                        )
                        if created:
                            created_count_for_file += 1
                
                if created_count_for_file > 0:
                    self.stdout.write(self.style.SUCCESS(f"'{filename}' 파일에서 {created_count_for_file}개의 새로운 단어를 등록했습니다."))
                total_created_count += created_count_for_file

        if total_created_count > 0:
            self.stdout.write(self.style.SUCCESS(f"\n총 {total_created_count}개의 새로운 유해 단어를 성공적으로 등록했습니다!"))
        else:
            self.stdout.write(self.style.NOTICE("\n새롭게 추가된 단어가 없습니다. 모든 단어가 이미 데이터베이스에 등록되어 있습니다."))