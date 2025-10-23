from django import forms
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth import get_user_model
from .models import CustomUser, UserSchedule, Vacation, Task, Tag
from datetime import datetime, time

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

        self.fields['department'].disabled = True
        self.fields['job_title'].widget.attrs['readonly'] = True

    def clean_department(self):
        return self.instance.department

    def clean_job_title(self):
        return self.instance.job_title


class CustomUserUpdateSchedule(forms.ModelForm):
    class Meta:
        model = UserSchedule
        fields = ('personal_hours_start', 'personal_hours_end')


class AddUserVacation(forms.ModelForm):
    class Meta:
        model = Vacation
        fields = ('date_start', 'date_end', 'tag')

        widgets = {
            'date_start': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'date_end': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user_schedule = kwargs.pop('user_schedule', None)

        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        date_start = cleaned_data.get('date_start')
        date_end = cleaned_data.get('date_end')

        if not date_start or not date_end:
            return cleaned_data

        if date_end < date_start:
            raise forms.ValidationError('Date End should be greater than Date Start')

        # проверка на пересечение с существующими записями
        if self.user_schedule:
            existing_vacations = Vacation.objects.filter(user_schedule=self.user_schedule)

            for vacation in existing_vacations:
                if not (date_end < vacation.date_start or date_start > vacation.date_end):
                    raise forms.ValidationError(
                        f'The vacation intersects with an existing period: '
                        f'{vacation.date_start} — {vacation.date_end}'
                    )

        return cleaned_data


class CreateTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ('head_task', 'title', 'managed_by', 'priority', 'deadline')
        widgets = {
            'deadline': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        managed_by = cleaned_data.get('managed_by')
        deadline = cleaned_data.get('deadline')

        if managed_by and deadline:
            validation_error = validate_task_time_for_user(managed_by, deadline)
            if validation_error:
                raise forms.ValidationError(validation_error)

        return cleaned_data


class EditeTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ('head_task', 'title', 'managed_by', 'priority', 'deadline', 'status')
        widgets = {
            'deadline': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        managed_by = cleaned_data.get('managed_by')
        deadline = cleaned_data.get('deadline')

        if managed_by and deadline:
            validation_error = validate_task_time_for_user(managed_by, deadline)
            if validation_error:
                raise forms.ValidationError(validation_error)

        return cleaned_data


def validate_task_time_for_user(user, deadline):
    task_date = deadline.date()
    task_time = deadline.time()

    try:
        user_schedule = UserSchedule.objects.get(user=user)

        if task_time < user_schedule.work_hours_start or task_time > user_schedule.work_hours_end:
            return f'Work hours: {user_schedule.work_hours_start.strftime('%H:%M')} - {user_schedule.work_hours_end.strftime('%H:%M')}'

        if user_schedule.personal_hours_start and user_schedule.personal_hours_end:
            if user_schedule.personal_hours_start <= task_time <= user_schedule.personal_hours_end:
                return f'Personal time: {user_schedule.personal_hours_start.strftime('%H:%M')} - {user_schedule.personal_hours_end.strftime('%H:%M')}'

        vacations = Vacation.objects.filter(
            user_schedule__user=user,
            date_start__lte=task_date,
            date_end__gte=task_date
        )

        if vacations.exists():
            vacation = vacations.first()
            return f'Vacation: {vacation.date_start} - {vacation.date_end}'

    except UserSchedule.DoesNotExist:
        return f'{user} schedule not found'

    return None

class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ('category', 'subcategory', 'for_what')