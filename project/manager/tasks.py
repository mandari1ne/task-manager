from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from textwrap import dedent
from smtplib import SMTPException
from django.conf import settings
from .models import Task, Notification

@shared_task
def deadline_reminders():
    now = timezone.now()
    reminder_time = now + timedelta(days=1)

    tasks = Task.objects.filter(
        status__name__in=['assigned', 'in progress', 'new'],
        deadline__date=reminder_time.date()
    )

    for task in tasks:
        user = task.managed_by
        tag = task.tag.to_tag() if task.tag else 'Good tag'

        text = dedent(f'''
            Task '{task.title} is approaching its deadline!'
            
            Task info:
                - Title: {task.title}
                - Deadline: {task.deadline}
                - Status: {task.status}
                - Tag: {tag}
        ''')

        if not Notification.objects.filter(task=task, type='Reminder'):
            Notification.objects.create(
                user=user,
                type='Reminder',
                message=text,
                task=task,
            )

        try:
            send_mail(
                subject='Task Deadline Reminder',
                message=text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.django_user.email],
                fail_silently=False,
            )
        except SMTPException:
            print('Ошибка отправки письма')
