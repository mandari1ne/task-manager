from datetime import time
from datetime import datetime, timedelta
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

from django.contrib.auth.models import User


@method_decorator(login_required(login_url='/login'), name='dispatch')
class IndexView(TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        users = User.objects.exclude(id=self.request.user.id).order_by('username')
        context['users'] = users


        return context


def get_tasks(request):
    selected_users = request.GET.getlist('users[]')

    if not selected_users:
        selected_users = [str(request.user.profile.id)]
    else:
        current_user_id = str(request.user.profile.id)
        if current_user_id not in selected_users:
            selected_users.append(current_user_id)

    start = request.GET.get("start")
    end = request.GET.get("end")

    # Преобразуем даты для Vacation (убираем время)
    start_date_only = start.split('T')[0] if start else None
    end_date_only = end.split('T')[0] if end else None

    events = []

    for user_id in selected_users:
        tasks_file = os.path.join(settings.STATIC_ROOT, f'tasks_user_{user_id}.json')

        use_cache = False
        user_events = []
        background_events = []

        if os.path.exists(tasks_file):
            try:
                with open(tasks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                data = {}

            last_task_update = models.Task.objects.filter(
                managed_by_id=user_id
            ).order_by('-updated_at').first()

            last_schedule_update = models.UserSchedule.objects.filter(
                user_id=user_id
            ).order_by('-id').first()

            last_vacation_update = models.Vacation.objects.filter(
                user_schedule__user_id=user_id
            ).order_by('-id').first()

            cache_valid = True
            if data.get('last_updated'):
                if (last_task_update and
                        last_task_update.updated_at.isoformat() != data.get('last_updated')):
                    cache_valid = False
                elif last_schedule_update:
                    # Простая проверка - если есть обновления в расписании, инвалидируем кэш
                    cache_valid = False
                elif last_vacation_update:
                    cache_valid = False

            if cache_valid and 'tasks' in data and 'background_events' in data:
                use_cache = True
                user_events = data['tasks']
                background_events = data['background_events']

        if not use_cache:
            # Загружаем задачи
            tasks = models.Task.objects.filter(
                managed_by_id=user_id,
                deadline__range=[start, end],
            ).select_related('status', 'managed_by').values(
                'id', 'title', 'deadline', 'status__name',
                'updated_at', 'managed_by_id', 'managed_by__django_user__first_name',
                'managed_by__django_user__last_name'
            )

            for task in tasks:
                status = task['status__name']
                css_slug = status.replace(' ', '-').lower()

                user_name = f"{task['managed_by__django_user__first_name']} {task['managed_by__django_user__last_name']}"

                user_events.append({
                    'id': str(task['id']),
                    'title': f"{task['title']} ({user_name})",
                    'start': task['deadline'].isoformat(),
                    'end': task['deadline'].isoformat(),
                    'status': task['status__name'],
                    'className': 'status-' + css_slug,
                    'user_id': str(task['managed_by_id']),
                    'user_name': user_name
                })

            # для рабочего времени
            try:
                schedule = models.UserSchedule.objects.get(user_id=user_id)

                start_date = datetime.fromisoformat(start).date()
                end_date = datetime.fromisoformat(end).date()

                day = start_date
                while day <= end_date:
                    work_start = datetime.combine(day, schedule.work_hours_start)
                    work_end = datetime.combine(day, schedule.work_hours_end)

                    day_start = datetime.combine(day, time(0, 0))
                    if day_start < work_start:
                        background_events.append({
                            'start': day_start.isoformat(),
                            'end': work_start.isoformat(),
                            'rendering': 'background',
                            'backgroundColor': '#1c1c1c',
                            'user_id': str(user_id),
                        })

                    day_end = datetime.combine(day, time(23, 59, 59))
                    if work_end < day_end:
                        background_events.append({
                            'start': work_end.isoformat(),
                            'end': day_end.isoformat(),
                            'rendering': 'background',
                            'backgroundColor': '#1c1c1c',
                            'user_id': str(user_id),
                        })

                    personal_start = datetime.combine(day, schedule.personal_hours_start)
                    personal_end = datetime.combine(day, schedule.personal_hours_end)
                    background_events.append({
                        'start': personal_start.isoformat(),
                        'end': personal_end.isoformat(),
                        'rendering': 'background',
                        'backgroundColor': '#585858',
                        'user_id': str(user_id),
                    })

                    day += timedelta(days=1)

                vacations = models.Vacation.objects.filter(
                    user_schedule__user_id=user_id,
                    date_end__gte=start_date_only,
                    date_start__lte=end_date_only,
                )

                for v in vacations:
                    background_events.append({
                        'start': v.date_start.isoformat(),
                        'end': (v.date_end + timedelta(days=1)).isoformat(),
                        'rendering': 'background',
                        'backgroundColor': '#363636',
                        'user_id': str(user_id),
                    })

                    start_datetime = datetime.combine(v.date_start, time(0, 0))
                    end_datetime = datetime.combine(v.date_end, time(23, 59, 59))

                    background_events.append({
                        'start': start_datetime.isoformat(),
                        'end': end_datetime.isoformat(),
                        'rendering': 'background',
                        'backgroundColor': '#363636',
                        'user_id': str(user_id),
                    })

            except models.UserSchedule.DoesNotExist:
                schedule = None

            # Сохраняем в кэш
            last_updated = max(task['updated_at'].isoformat() for task in tasks) if tasks else ''
            with open(tasks_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'last_updated': last_updated,
                    'tasks': user_events,
                    'background_events': background_events
                }, f, ensure_ascii=False, indent=4)

        events.extend(user_events)
        events.extend(background_events)

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

    # создана ли задача текущим пользователем и кто ее выполняет
    can_edit = task.created_by == request.user.profile or task.managed_by == request.user.profile

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
        'can_edit': can_edit,
    })


def delete_task(request, task_id):
    try:
        task = models.Task.objects.get(id=task_id)

        task_title = task.title
        task.delete()

        return JsonResponse({
            'success': True,
            'message': f'Task {task_title} deleted successfully',
        })
    except models.Task.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Task not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e),
        }, status=500)
