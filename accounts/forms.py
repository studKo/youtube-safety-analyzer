from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

# settings.py에 정의된 AUTH_USER_MODEL을 가져옵니다. (accounts.User)
User = get_user_model()

# 로그인 폼
class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='학번',
        widget=forms.TextInput(attrs={'autofocus': True})
    )
    password = forms.CharField(
        label='비밀번호',
        strip=False,
        widget=forms.PasswordInput,
    )

# 회원가입 폼
class RegisterForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name')
        labels = {
            'username': '학번',
            'first_name': '이름',
        }

    # ⭐️ 학번(username) 유효성 검사 메서드 수정
    def clean_username(self):
        username = self.cleaned_data.get('username')
        
        # 학번 형식 검사
        if not username.isdigit():
            raise ValidationError("학번은 숫자로만 구성되어야 합니다.")
        if len(username) > 12:
            raise ValidationError("학번은 12자리를 초과할 수 없습니다.")
            
        # ⭐️ 학번 중복 검사 로직 추가
        # UserCreationForm이 username 중복은 확인하지만, student_id 중복도 확인해야 합니다.
        if User.objects.filter(student_id=username).exists():
            raise ValidationError("이미 가입된 학번입니다.")
            
        return username

    # User 모델의 student_id 필드에도 학번을 저장하기 위한 save 메서드
    def save(self, commit=True):
        user = super().save(commit=False)
        user.student_id = self.cleaned_data['username']
        if commit:
            user.save()
        return user