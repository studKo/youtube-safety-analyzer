# CapstoneProjectCSS02/config/urls.py 파일의 전체 내용입니다.

from django.contrib import admin
from django.urls import path, include
from youtube_analysis import views
# ⭐️ 아래 두 줄이 추가되었습니다.
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # 메인 페이지('/') 접속 시 youtube_analysis 앱의 youtube_page 뷰를 보여줌
    path('', views.youtube_page, name='home'),
    # '/youtube/'으로 시작하는 모든 주소를 youtube_analysis 앱의 urls.py 파일로 연결
    path('youtube/', include('youtube_analysis.urls')),
    # '/accounts/'로 시작하는 주소는 accounts 앱의 urls.py로 연결
    path('accounts/', include('accounts.urls')),
]

# ⭐️ 이 부분이 추가되었습니다.
# DEBUG 모드일 때 static 파일과 media 파일을 Django 개발 서버에서 제공하도록 설정
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)