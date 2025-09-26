from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User  # ⭐️ 'StudentUser'를 'User'로 수정했습니다.

# Django 관리자 페이지에 우리가 만든 User 모델을 등록합니다.
# UserAdmin을 함께 등록하면 관리자 페이지에서 사용자를 편리하게 관리할 수 있습니다.
admin.site.register(User, UserAdmin)