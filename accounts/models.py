from django.contrib.auth.models import AbstractUser
from django.db import models

# Django의 기본 사용자 모델을 확장하여 우리 프로젝트에 맞는 User 모델을 정의
class User(AbstractUser):

    student_id = models.CharField(max_length=20, unique=True, verbose_name='학번')

    first_name = models.CharField(max_length=150, blank=True, verbose_name='이름')

    REQUIRED_FIELDS = ['student_id']

    def __str__(self):
        return self.username