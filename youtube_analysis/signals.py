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
    VerifiedSentence 객체가 저장될 때마다, CSV 파일을 '업데이트'합니다.
    (수정) CSV 파일에 이미 중복된 문장이 있다면, 
    이 시그널이 실행될 때 중복을 제거하고 단 하나의 행만 남깁니다.
    """
    
    file_path = os.path.join(settings.BASE_DIR, 'verified_data.csv')
    header = ['text', 'label']
    file_exists = os.path.isfile(file_path)
    
    # 1. 현재 DB 인스턴스(문장)의 상태
    current_sentence = instance.original_sentence
    current_label = instance.human_verification # 'positive', 'negative', 'neutral', or None
    
    existing_rows = []
    
    # 2. 기존 CSV 파일 내용을 (있다면) 모두 읽어들임
    if file_exists:
        try:
            with open(file_path, 'r', newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.reader(csvfile)
                try:
                    read_header = next(reader)
                    if read_header != header:
                        existing_rows.append(read_header) 
                    existing_rows.extend(list(reader))
                except StopIteration:
                    pass 
        except Exception as e:
            print(f"CSV 읽기 오류 (무시하고 덮어쓰기 진행): {e}")
            existing_rows = [] 
    
    # 3. CSV에 새로 쓸 데이터 목록을 만듦
    new_rows_to_write = []
    new_rows_to_write.append(header) # 헤더는 항상 목록의 가장 처음에 추가
    
    # (추가된 로직) 이 문장을 처리했는지 여부를 추적하는 플래그
    sentence_processed_flag = False 
    
    for row in existing_rows:
        if not row: # 빈 줄 스킵
            continue
            
        row_sentence = row[0]
        
        # 현재 저장된 DB 인스턴스와 같은 문장인지 확인
        if row_sentence == current_sentence:
            
            # (추가된 로직) 이 문장을 CSV에서 '처음' 발견한 경우
            if not sentence_processed_flag:
                sentence_processed_flag = True # 처리했다고 표시
                
                if current_label:
                    # 라벨이 있으면 -> 업데이트된 라벨로 추가
                    new_rows_to_write.append([current_sentence, current_label])
                # else:
                    # 라벨이 None (비어있음)이 되면 -> 추가하지 않음 (즉, 삭제 효과)
            
            # else:
                # (추가된 로직) 이 문장을 '두 번째' (혹은 그 이상) 발견한 경우
                # 즉, 기존 CSV에 있던 '중복' 데이터이므로,
                # new_rows_to_write에 추가하지 않고 무시합니다. (중복 제거 효과)
                pass 
                
        else:
            # 다른 문장이면 -> 기존 내용 그대로 추가
            new_rows_to_write.append(row)
    
    # 4. (수정된 로직) 기존 CSV에 이 문장이 '한 번도' 없었고(신규), 새 라벨이 있다면 -> 새 행으로 추가
    if not sentence_processed_flag and current_label:
        new_rows_to_write.append([current_sentence, current_label])

    # 5. 새로운 내용으로 CSV 파일 전체를 덮어쓰기 ('w' 모드)
    try:
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(new_rows_to_write)
    except Exception as e:
        print(f"CSV 쓰기 오류: {e}")