from wsgiref.util import request_uri

from django.conf import settings
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
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
        ).values('id', 'title', 'deadline', 'status__name', 'updated_at')

        events = []
        for task in tasks:
            status = task['status__name']
            css_slug = status.replace(' ', '-').lower()

            events.append({
                'id': str(task['id']),
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

@login_required(login_url='/login')
def add_vacation(request):
    django_user = request.user
    custom_user = django_user.profile
    user_schedule = custom_user.schedule

    if request.method == 'POST':
        vacation_form = forms.AddUserVacation(request.POST, user_schedule=user_schedule)

        if vacation_form.is_valid():
            vacation = vacation_form.save(commit=False)
            vacation.user_schedule = user_schedule

            vacation.save()

            messages.success(request, 'Vacation added successful')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return HttpResponse(status=200)
            else:
                return redirect('add_vacation')

        else:
            messages.error(request, 'Please, fix the errors')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return render(request, 'add_vacation.html', {'vacation_form': vacation_form})

    else:
        vacation_form = forms.AddUserVacation(user_schedule=user_schedule)

    context = {
        'vacation_form': vacation_form,
    }

    return render(request, 'add_vacation.html', context)

def create_task(request):
    django_user = request.user
    custom_user = django_user.profile

    if request.method == 'POST':
        task_form = forms.CreateTaskForm(request.POST)
        tag_form = forms.TagForm(request.POST)

        if task_form.is_valid() and tag_form.is_valid():
            task = task_form.save(commit=False)
            task.created_by = custom_user
            task.status = models.Status.objects.get(name='new')
            task.save()

            tag = tag_form.save(commit=False)
            tag.task = task
            tag.save()

            messages.success(request, 'Task created successfully!')
            return redirect('index')
        else:
            messages.error(request, 'Please fix the errors')
    else:
        task_form = forms.CreateTaskForm()
        tag_form = forms.TagForm()

    return render(request, 'create_task.html', {
        'task_form': task_form,
        'tag_form': tag_form,
    })

def edit_task(request, task_id):
    task = get_object_or_404(models.Task, id=task_id)
    tag = task.tag

    if request.method == 'POST':
        task_form = forms.EditeTaskForm(request.POST, instance=task)
        tag_form = forms.TagForm(request.POST, instance=tag)

        if task_form.is_valid() and tag_form.is_valid():
            task_form.save()
            tag_form.save()

            messages.success(request, 'Task updated successfully')
            return redirect('index')

        else:
            messages.error(request, 'Please fix the errors  bellow')

    else:
        task_form = forms.EditeTaskForm(instance=task)
        tag_form = forms.TagForm(instance=tag)

    return render(request, 'edit_task.html', {
        'task_form': task_form,
        'tag_form': tag_form,
        'task': task,
    })
