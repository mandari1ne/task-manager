from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.contrib import messages
from . import models, forms
import json, os

@method_decorator(login_required(login_url='/login'), name='dispatch')
class IndexView(TemplateView):
    template_name = 'index.html'

def get_tasks(request):
    # request.user.profile - ЗАМЕНИТЬ НАДО БУДЕТ
    # test_user = models.CustomUser.objects.get(django_user__username='user')
    current_user = request.user.profile
    current_user_id = current_user.id

    tasks_dir = settings.STATIC_ROOT

    # создем, если не существует
    os.makedirs(tasks_dir, exist_ok=True)
    tasks_file = os.path.join(tasks_dir, f'tasks_user_{current_user_id}.json')

    start = request.GET.get("start")
    end = request.GET.get("end")

    use_cache = False
    if os.path.exists(tasks_file):
        try:
            with open(tasks_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = {}

        last_task_update = models.Task.objects.filter(managed_by=current_user).order_by('-updated_at').first()
        if last_task_update:
            if data.get('last_updated') == last_task_update.updated_at.isoformat():
                use_cache = True
                tasks = data['tasks']

    if use_cache:
        events = data['tasks']
    else:
        tasks = models.Task.objects.filter(
            managed_by=current_user,
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


@login_required(login_url='/login')
def profile_view(request):
    django_user = request.user
    custom_user = django_user.profile

    if request.method == 'POST':
        django_user_form = forms.DjangoUserChangeForm(request.POST, instance=django_user)
        custom_user_form = forms.CustomUserUpdateForm(request.POST, request.FILES, instance=custom_user)

        print("=== DEBUG ===")
        print("FILES:", request.FILES)

        if django_user_form.is_valid() and custom_user_form.is_valid():
            print("Forms are VALID - SAVING!")
            django_user_form.save()
            custom_user_form.save()
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('profile')
        else:
            print("=== FORM ERRORS ===")
            print("DjangoUser errors:", django_user_form.errors)
            print("CustomUser errors:", custom_user_form.errors)
            print("=== END ERRORS ===")
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')

    else:
        django_user_form = forms.DjangoUserChangeForm(instance=django_user)
        custom_user_form = forms.CustomUserUpdateForm(instance=custom_user)

    context = {
        'django_user_form': django_user_form,
        'custom_user_form': custom_user_form,
        'custom_user': custom_user,
    }

    return render(request, 'profile.html', context)
