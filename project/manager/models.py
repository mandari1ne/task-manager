from django.db import models
from django.conf import settings
from django.utils.html import strip_tags

from django.utils import timezone
from datetime import datetime, timedelta, time


def default_deadline():
    today = timezone.now().date()
    deadline_date = today + timedelta(days=3)

    # дата=сегодня + 3, время 00:00
    return timezone.make_aware(datetime.combine(deadline_date, time.min))


class CustomUser(models.Model):
    django_user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                       on_delete=models.CASCADE,
                                       related_name="profile")
    patronymic = models.CharField(max_length=255, blank=True, null=True)
    department = models.ForeignKey('Department',
                                   on_delete=models.CASCADE,
                                   related_name='employees')
    job_title = models.CharField(max_length=255)
    user_img = models.ImageField(upload_to='users/')
    telegram_username = models.CharField(max_length=100)

    def clean(self):
        for field in ['patronymic', 'job_title', 'telegram_username']:
            value = getattr(self, field)

            if value:
                setattr(self, field, strip_tags(value))

            if self.telegram_username and not self.telegram_username.startswith('@'):
                self.telegram_username = '@' + self.telegram_username


class Department(models.Model):
    name = models.CharField(max_length=255)
    head_person = models.OneToOneField('CustomUser',
                                       on_delete=models.CASCADE,
                                       related_name='headed_department',
                                       blank=True, null=True)

    def __str__(self):
        return self.name


class Holiday(models.Model):
    department = models.ManyToManyField(Department,
                                        related_name='holidays')
    name = models.CharField(max_length=255)
    date_time_start = models.DateTimeField()
    date_time_end = models.DateTimeField()

    def __str__(self):
        return self.name


class Status(models.Model):
    name = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.name


class Task(models.Model):
    head_task = models.ForeignKey('self',
                                  on_delete=models.CASCADE,
                                  related_name='subtasks',
                                  null=True, blank=True)
    title = models.CharField(max_length=255)
    assigned_by = models.ForeignKey(CustomUser,
                                    on_delete=models.CASCADE,
                                    related_name='assigned_tasks',
                                    null=True, blank=True)
    managed_by = models.ForeignKey(CustomUser,
                                   on_delete=models.CASCADE,
                                   related_name='managed_tasks',
                                   null=True, blank=True)
    created_by = models.ForeignKey(CustomUser,
                                   on_delete=models.CASCADE,
                                   related_name='created_tasks',
                                   null=True, blank=True)
    priority = models.BooleanField(default=True)
    deadline = models.DateTimeField(default=default_deadline)
    status = models.ForeignKey(Status,
                               on_delete=models.CASCADE,
                               related_name='tasks',
                               null=True, blank=True)

    def __str__(self):
        return f'{self.title} - {self.status} - {self.deadline}'


class Tag(models.Model):
    task = models.ManyToManyField(Task,
                             related_name='tags')
    category = models.CharField(max_length=100, blank=True, null=True)
    subcategory = models.CharField(max_length=100, blank=True, null=True)
    for_what = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Tag for task: {self.task.title}"

    def to_tag(self):
        parts = []

        for field in [self.category, self.subcategory]:
            parts.append(field if field else '_')

        parts.append(self.for_what if self.for_what else '_')

        return '#' + '-'.join(parts)

    def to_description(self, tag):
        parts = tag[1:].split('-')

        new_parts = [p if p != '_' else None for p in parts]

        self.category = new_parts[0]
        self.subcategory = new_parts[1]
        self.for_what = new_parts[2]


class Notification(models.Model):
    user = models.ForeignKey(CustomUser,
                             on_delete=models.CASCADE,
                             related_name='notifications')
    type = models.CharField(max_length=150)
    send_time = models.DateTimeField(default=timezone.now)
    message = models.TextField()
    task = models.ForeignKey(Task,
                             on_delete=models.CASCADE,
                             related_name='notifications')

    def __str__(self):
        return f'Notification for {self.user} - {self.type}'


class UserSchedule(models.Model):
    user = models.OneToOneField(CustomUser,
                                on_delete=models.CASCADE,
                                related_name='schedule')
    work_hours_start = models.TimeField()
    work_hours_end = models.TimeField()
    personal_hours_start = models.TimeField()
    personal_hours_end = models.TimeField()

    def __str__(self):
        return f'Schedule for {self.user.django_user.first_name} {self.user.django_user.last_name}'


class Vacation(models.Model):
    user_schedule = models.ForeignKey(UserSchedule,
                                      on_delete=models.CASCADE,
                                      related_name='vacations')
    date_start = models.DateField()
    date_end = models.DateField()
    tag = models.CharField(max_length=100)
