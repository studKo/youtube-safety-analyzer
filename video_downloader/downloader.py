# new/video_downloader/downloader.py

import yt_dlp
import os

# 연령 제한 오류를 위한 사용자 정의 예외 클래스 생성
class AgeRestrictedError(Exception):
    """연령 제한 콘텐츠에 대한 사용자 정의 예외"""
    pass

def download_audio_from_youtube(url, output_dir="."):
    """
    yt-dlp를 사용하여 YouTube 영상의 연령 제한 여부를 먼저 확인하고,
    제한이 없는 경우에만 음성을 추출하여 mp3 파일로 저장합니다.
    
    Args:
        url (str): YouTube 영상 URL
        output_dir (str): 음성 파일을 저장할 디렉토리

    Returns:
        tuple: (저장된 오디오 파일의 전체 경로, 영상 제목)
        
    Raises:
        AgeRestrictedError: 영상이 연령 제한 콘텐츠일 경우 발생
    """
    
    # 1. 연령 제한 여부만 먼저 확인하기 위한 옵션
    check_opts = {
        'quiet': True,
        'no_warnings': True,
        'simulate': True, # 실제로 다운로드하지 않고 정보만 가져옴
    }

    with yt_dlp.YoutubeDL(check_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        age_limit = info_dict.get('age_limit', 0)
        
        # 연령 제한이 있으면, 직접 만든 AgeRestrictedError를 발생시킴
        if age_limit > 0:
            raise AgeRestrictedError("이 영상은 연령 제한 콘텐츠이므로 분석할 수 없습니다.")

    # 2. 연령 제한이 없을 경우, 실제 다운로드를 진행하는 옵션
    download_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(output_dir, '%(title)s [%(id)s].%(ext)s'),
        'restrictfilenames': True,
    }

    with yt_dlp.YoutubeDL(download_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        video_title = info_dict.get('title', None)
        
        original_filepath = ydl.prepare_filename(info_dict)
        final_filepath = os.path.splitext(original_filepath)[0] + '.mp3'

    return final_filepath, video_title