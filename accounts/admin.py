# new/accounts/admin.py

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

# settings.AUTH_USER_MODEL에 연결된 실제 User 모델을 가져옵니다.
User = get_user_model()

class CustomUserAdmin(UserAdmin):
    """
    기본 사용자 관리자 페이지를 확장하여 커스텀 필드와 필터를 추가합니다.
    """
    # 목록 페이지에 보여줄 필드를 설정합니다. 'student_id'와 'first_name'을 추가합니다.
    list_display = ('username', 'student_id', 'first_name', 'is_staff', 'is_superuser')
    
    # 오른쪽 사이드바에 필터 옵션을 추가합니다. 'is_staff'로 관리자와 일반 사용자를 구분할 수 있습니다.
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    
    # 사용자 정보 수정 페이지에 'student_id' 필드를 추가합니다.
    # 기존 UserAdmin의 필드 설정에 '추가 정보' 섹션을 더합니다.
    fieldsets = UserAdmin.fieldsets + (
        ('추가 정보', {'fields': ('student_id',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('추가 정보', {'fields': ('student_id', 'first_name')}),
    )

# 기존에 등록된 User 모델이 있다면 등록 해제하고, 새로 만든 CustomUserAdmin으로 다시 등록합니다.
# 이 코드는 admin.py가 처음 로드될 때 User가 이미 등록되어 있을 경우를 대비합니다.
if admin.site.is_registered(User):
    admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)