# youtube_analysis/management/commands/import_badwords.py

import os
from django.core.management.base import BaseCommand
from django.conf import settings
from youtube_analysis.models import BadWord

class Command(BaseCommand):
    """
    (단어,가중치) 형식으로 분리된 유해 단어 .txt 파일들을 읽어와 
    데이터베이스에 자동으로 저장합니다.
    사용법: python manage.py import_badwords
    """
    help = "(단어,가중치) 형식의 .txt 사전을 데이터베이스에 자동으로 등록합니다."

    def handle(self, *args, **options):
        """
        명령어가 실행될 때 호출되는 메인 로직입니다.
        """
        # 처리할 파일 목록: (파일명, DB에 저장될 카테고리명)
        # 가중치는 이제 파일 내부에서 읽어옵니다.
        files_to_import = [
            ('badwords_profanity.txt', 'profanity'),
            ('badwords_hate_speech.txt', 'hate_speech'),
            ('badwords_discrimination.txt', 'discrimination'),
            ('badwords_violence.txt', 'violence'),
        ]

        self.stdout.write(self.style.SUCCESS("유해 단어 자동 등록(단어,가중치)을 시작합니다..."))
        total_created_count = 0

        # 데이터베이스의 모든 유해 단어를 한번에 삭제 (초기화)
        # 주의: 이 줄의 주석을 해제하면, 명령어 실행 시마다 DB가 초기화됩니다.
        BadWord.objects.all().delete()
        self.stdout.write(self.style.WARNING("기존의 모든 유해 단어를 삭제했습니다."))

        for filename, category in files_to_import:
            file_path = os.path.join(settings.BASE_DIR, filename)
            
            if not os.path.exists(file_path):
                self.stdout.write(self.style.WARNING(f"'{filename}' 파일을 찾을 수 없어 건너뜁니다."))
                continue

            with open(file_path, 'r', encoding='utf-8') as f:
                created_count_for_file = 0
                # 라인 번호를 함께 추적하여 오류 리포팅을 개선합니다.
                for line_number, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # 빈 줄은 건너뜁니다.
                    if not line:
                        continue

                    try:
                        # 1. 라인을 쉼표(,) 기준으로 분리합니다.
                        parts = line.split(',')
                        
                        # 2. 형식이 맞는지 검사 (정확히 2부분이어야 함)
                        if len(parts) != 2:
                            raise ValueError("쉼표(,)로 구분된 '단어,숫자' 형식이 아닙니다.")
                        
                        # 3. 단어와 가중치를 추출하고 공백을 제거합니다.
                        word = parts[0].strip().lower()
                        weight = int(parts[1].strip()) # 가중치를 정수로 변환
                        
                        # 4. 단어가 비어있지 않은지 확인
                        if not word:
                            raise ValueError("단어가 비어있습니다.")

                        # 5. DB에 저장 (get_or_create 사용)
                        #    파일에서 읽어온 'weight'를 defaults에 동적으로 전달합니다.
                        _, created = BadWord.objects.get_or_create(
                            word=word,
                            defaults={
                                'category': category,
                                'weight': weight, # 파일에서 읽어온 가중치 적용
                            }
                        )
                        if created:
                            created_count_for_file += 1
                    
                    # 6. 형식 오류 처리 (ValueError)
                    except ValueError as e:
                        self.stdout.write(self.style.WARNING(
                            f"-> 경고: '{filename}' 파일 {line_number}번째 줄 오류: '{line}'. (이유: {e}) -> 이 줄은 건너뜁니다."
                        ))
                    # 7. 기타 예외 처리
                    except Exception as e:
                         self.stdout.write(self.style.ERROR(
                            f"-> 심각: '{filename}' 파일 {line_number}번째 줄 처리 중 예외 발생: {e}"
                        ))

                
                if created_count_for_file > 0:
                    self.stdout.write(self.style.SUCCESS(f"'{filename}' 파일에서 {created_count_for_file}개의 새로운 단어를 등록했습니다."))
                total_created_count += created_count_for_file

        if total_created_count > 0:
            self.stdout.write(self.style.SUCCESS(f"\n총 {total_created_count}개의 새로운 유해 단어를 성공적으로 등록했습니다!"))
        else:
            self.stdout.write(self.style.NOTICE("\n새롭게 추가된 단어가 없습니다. 모든 단어가 이미 데이터베이스에 등록되어 있습니다."))