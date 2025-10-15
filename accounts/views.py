# new/accounts/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, LoginForm
from django.conf import settings
from youtube_analysis.models import Transcription
from collections import defaultdict

def register_view(request):
    """
    회원가입 페이지를 처리하는 뷰입니다.
    """
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL)
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    """
    로그인 페이지를 처리하는 뷰입니다.
    """
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect(request.GET.get('next') or settings.LOGIN_REDIRECT_URL)
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    """
    로그아웃을 처리하는 뷰입니다.
    """
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)

@login_required
def mypage_view(request):
    """
    마이페이지를 렌더링하고, 비교 분석이 가능한 항목을 찾아 전달합니다.
    """
    # --- [ 쿼리 최적화 적용 ] ---
    # select_related('user')를 사용하여 Transcription과 User 테이블을 한 번의 쿼리로 함께 조회합니다.
    # 이를 통해 N+1 문제를 해결하고 데이터베이스 접근 횟수를 최소화합니다.
    user_transcriptions = Transcription.objects.select_related('user').filter(user=request.user).order_by('-created_at')
    # --- [        끝        ] ---

    # URL별로 분석 기록을 그룹화하기 위한 딕셔너리
    grouped_transcriptions = defaultdict(list)
    for trans in user_transcriptions:
        grouped_transcriptions[trans.youtube_url].append(trans)

    # 템플릿에 전달할 최종 데이터 리스트
    processed_list = []
    
    # 이미 처리된 URL을 추적하기 위한 집합
    handled_urls = set()

    for trans in user_transcriptions:
        url = trans.youtube_url
        if url in handled_urls:
            continue

        group = grouped_transcriptions[url]
        
        # 동일 URL에 대해 2개 이상의 분석 기록이 있고, 모델이 서로 다른 경우
        if len(group) >= 2:
            kcbert_result = next((t for t in group if 'kcbert' in t.model_name.lower()), None)
            roberta_result = next((t for t in group if 'roberta' in t.model_name.lower()), None)
            
            # 두 모델의 결과가 모두 존재하면, 비교 분석 항목으로 처리
            if kcbert_result and roberta_result:
                processed_list.append({
                    'is_comparison': True,
                    'title': kcbert_result.title,
                    'youtube_url': url,
                    'kcbert_id': kcbert_result.id,
                    'roberta_id': roberta_result.id,
                    'created_at': kcbert_result.created_at
                })
                handled_urls.add(url)
            else: # 두 모델이 모두 있지는 않은 경우
                processed_list.append({'is_comparison': False, 'transcription': trans})
                handled_urls.add(url)
        else: # 분석 기록이 하나뿐인 경우
            processed_list.append({'is_comparison': False, 'transcription': trans})
            handled_urls.add(url)

    context = {
        'processed_list': processed_list
    }
    return render(request, 'mypage.html', context)