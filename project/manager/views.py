from django.conf import settings
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse, HttpResponse
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

    try:
        user_schedule = custom_user.schedule
    except models.UserSchedule.DoesNotExist:
        user_schedule = {
            'personal_hours_start': '',
            'personal_hours_end': '',
        }

    if request.method == 'POST':
        django_user_form = forms.DjangoUserChangeForm(request.POST, instance=django_user)
        custom_user_form = forms.CustomUserUpdateForm(request.POST, request.FILES, instance=custom_user)
        schedule_form = forms.CustomUserUpdateSchedule(request.POST, instance=user_schedule)

        if django_user_form.is_valid() and custom_user_form.is_valid() and schedule_form.is_valid():
            django_user_form.save()
            custom_user_form.save()
            schedule_form.save()

            messages.success(request, 'Profile changed successful')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the errors in the form')

    else:
        django_user_form = forms.DjangoUserChangeForm(instance=django_user)
        custom_user_form = forms.CustomUserUpdateForm(instance=custom_user)
        schedule_form = forms.CustomUserUpdateSchedule(instance=user_schedule)

    context = {
        'django_user_form': django_user_form,
        'custom_user_form': custom_user_form,
        'schedule_form': schedule_form,
        'custom_user': custom_user,
    }

    return render(request, 'profile.html', context)


@login_required(login_url='/login')
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)

        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            return JsonResponse({
                'success': True,
                'message': 'The password has been successfully changed'
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors,
                'message': 'Please correct the errors in the form.'
            })

    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'change_password_modal.html', {'form': form})

def get_personal_time(request):
    current_user = request.user.profile

    try:
        user_schedule = models.UserSchedule.objects.get(user=current_user)
        hours = {
            'personal_hours_start': user_schedule.personal_hours_start,
            'personal_hours_end': user_schedule.personal_hours_end,
        }
    except models.UserSchedule.DoesNotExist:
        hours = {}

    return JsonResponse(hours)
