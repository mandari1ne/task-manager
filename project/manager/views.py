from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import TemplateView
from . import models
import json, os


class IndexView(TemplateView):
    template_name = 'index.html'

def get_tasks(request):
    # request.user.profile - ЗАМЕНИТЬ НАДО БУДЕТ
    test_user = models.CustomUser.objects.get(django_user__username='user')
    test_user_id = test_user.id

    tasks_dir = settings.STATIC_ROOT

    # создем, если не существует
    os.makedirs(tasks_dir, exist_ok=True)
    tasks_file = os.path.join(tasks_dir, f'tasks_user_{test_user_id}.json')

    start = request.GET.get("start")
    end = request.GET.get("end")

    use_cache = False
    if os.path.exists(tasks_file):
        try:
            with open(tasks_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = {}

        last_task_update = models.Task.objects.filter(managed_by=test_user).order_by('-updated_at').first()
        if last_task_update:
            if data.get('last_updated') == last_task_update.updated_at.isoformat():
                use_cache = True
                tasks = data['tasks']

    if use_cache:
        events = data['tasks']
    else:
        tasks = models.Task.objects.filter(
            managed_by=test_user,
            deadline__range=[start, end],
        ).values('title', 'deadline', 'status__name', 'updated_at')

        events = []
        for task in tasks:
            status = task['status__name']
            css_slug = status.replace(' ', '-').lower()

            events.append({
                'title': task['title'],
                'start': task['deadline'].isoformat(),
                'end': task['deadline'].isoformat(),
                'status': task['status__name'],
                'className': 'status-' + css_slug,
            })

        last_updated = max(task['updated_at'].isoformat() for task in tasks) if tasks else ''
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump({
                'last_updated': last_updated,
                'tasks': events
            }, f, ensure_ascii=False, indent=4)

    return JsonResponse(events, safe=False)
