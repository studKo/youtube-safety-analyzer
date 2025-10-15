# new/video_downloader/downloader.py

import yt_dlp
import os
import shutil
import subprocess # ⭐️ FFmpeg을 직접 호출하기 위해 subprocess 라이브러리 추가

class AgeRestrictedError(Exception):
    """연령 제한 콘텐츠에 대한 사용자 정의 예외"""
    pass

def download_audio_from_youtube(url_or_path, output_dir="."):
    """
    YouTube URL 또는 로컬 파일 경로를 받아 오디오(mp3)를 준비합니다.
    """
    
    # ✅ 1. 입력값이 로컬 파일 경로인지 먼저 확인합니다.
    if os.path.exists(url_or_path):
        print(f"✅ 로컬 파일 감지: {url_or_path}")
        file_name = os.path.basename(url_or_path)
        destination_path = os.path.join(output_dir, file_name)

        # 파일을 media 폴더로 복사
        shutil.copy(url_or_path, destination_path)
        
        # 동영상 확장자 목록
        video_extensions = ['.mp4', '.mkv', '.webm', '.mov', '.avi']
        file_ext = os.path.splitext(file_name)[1].lower()

        # ✅ 2. 만약 비디오 파일이면 FFmpeg으로 mp3를 추출합니다.
        if file_ext in video_extensions:
            print(f"✅ 비디오 파일 감지, FFmpeg으로 MP3 변환 시작...")
            mp3_path = os.path.splitext(destination_path)[0] + '.mp3'
            
            try:
                # FFmpeg 명령어를 직접 실행하여 오디오 추출
                # 명령어: ffmpeg -i "원본영상.mp4" -vn -ar 44100 -ac 2 -b:a 192k "결과오디오.mp3"
                subprocess.run([
                    'ffmpeg', '-i', destination_path, 
                    '-vn',  # 비디오 제외
                    '-ar', '44100', # 오디오 샘플링 레이트
                    '-ac', '2', # 오디오 채널 (스테레오)
                    '-b:a', '192k', # 오디오 비트레이트
                    mp3_path
                ], check=True, capture_output=True) # check=True는 오류 발생 시 예외를 발생시킴
                
                os.remove(destination_path) # 변환이 끝난 원본 비디오 파일 삭제
                return mp3_path, os.path.basename(mp3_path) # mp3 경로와 파일명 반환
            except subprocess.CalledProcessError as e:
                # 변환 실패 시 에러 메시지 출력 및 파일 정리
                print(f"❌ FFmpeg 오디오 변환 실패: {e.stderr.decode()}")
                if os.path.exists(destination_path): os.remove(destination_path)
                if os.path.exists(mp3_path): os.remove(mp3_path)
                raise e # 에러를 다시 발생시켜 상위 함수에서 처리하도록 함
        
        # 비디오 파일이 아니라면 (예: mp3 파일) 복사된 경로와 파일명 바로 반환
        return destination_path, file_name

    # --- 여기서부터는 기존의 YouTube URL 처리 로직입니다 ---
    # ✅ 3. 로컬 파일이 아닐 경우에만 yt-dlp로 URL 분석을 시도합니다.
    check_opts = {'quiet': True, 'no_warnings': True, 'simulate': True}
    with yt_dlp.YoutubeDL(check_opts) as ydl:
        info_dict = ydl.extract_info(url_or_path, download=False)
        if info_dict.get('age_limit', 0) > 0:
            raise AgeRestrictedError("이 영상은 연령 제한 콘텐츠이므로 분석할 수 없습니다.")

    download_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
        'outtmpl': os.path.join(output_dir, '%(title)s [%(id)s].%(ext)s'),
        'restrictfilenames': True,
    }
    with yt_dlp.YoutubeDL(download_opts) as ydl:
        info_dict = ydl.extract_info(url_or_path, download=True)
        video_title = info_dict.get('title', None)
        original_filepath = ydl.prepare_filename(info_dict)
        final_filepath = os.path.splitext(original_filepath)[0] + '.mp3'
    
    return final_filepath, video_title