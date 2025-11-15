from smtplib import SMTPException
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from .models import Notification, Tag, Task
from django.core.mail import send_mail
from django.conf import settings
from textwrap import dedent

@receiver(post_save, sender=Task)
def notify_then_update(sender, instance, created, **kwargs):
    task = instance
    user = task.managed_by
    tag = task.tag.to_tag() if task.tag else "Good tag, isn't it"

    if created:
        text = dedent(f"""
                    Task "{task.title}" was created.

                    Task info:
                        - Title: {task.title}
                        - Deadline: {task.deadline}
                        - Status: {task.status}
                        - Tag: {tag}
                """)

        Notification.objects.create(
            user=user,
            type='Create',
            message=text,
            task=task,
        )

        try:
            send_mail(
                'Creating task',
                message=text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.django_user.email],
                fail_silently=False,
            )
        except SMTPException:
            print('Ошибка отправки письма')

    elif not created:
        text = dedent(f"""
            Task "{task.title}" was updated.

            Task info:
                - Title: {task.title}
                - Deadline: {task.deadline}
                - Status: {task.status}
                - Tag: {tag}
        """)

        Notification.objects.create(
            user=user,
            type='Update',
            message=text,
            task=task,
        )

        try:
            send_mail(
                'Updating task',
                message=text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.django_user.email],
                fail_silently=False,
            )
        except SMTPException:
            print('Ошибка отправки письма')

@receiver(pre_delete, sender=Task)
def notify_then_delete(sender, instance, **kwargs):
    task = instance
    user = task.managed_by
    tag = task.tag.to_tag() if task.tag else "Good tag, isn't it"

    text = dedent(f"""
                    Task "{task.title}" was deleted.

                    Task info:
                        - Title: {task.title}
                        - Deadline: {task.deadline}
                        - Status: {task.status}
                        - Tag: {tag}
                """)

    Notification.objects.create(
        user=user,
        type='Create',
        message=text,
        task=task,
    )

    if text:
        try:
            send_mail(
                'Deleting task',
                message=text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.django_user.email],
                fail_silently=False,
            )
        except SMTPException:
            print('Ошибка отправки письма')
