from django import forms
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth import get_user_model
from .models import CustomUser


User = get_user_model()

class DjangoUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'password' in self.fields:
            del self.fields['password']


class CustomUserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('user_img', 'department', 'job_title', 'patronymic', 'telegram_username')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем поля только для чтения, но они будут передаваться в форме
        self.fields['department'].disabled = True
        self.fields['job_title'].widget.attrs['readonly'] = True

    def clean_department(self):
        # Всегда возвращаем текущее значение
        return self.instance.department

    def clean_job_title(self):
        # Всегда возвращаем текущее значение
        return self.instance.job_title
