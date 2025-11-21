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
from django.utils.dateparse import parse_datetime
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

    start_dt = parse_datetime(start) if start else None
    end_dt = parse_datetime(end) if end else None

    start_date_only = start.split('T')[0] if start else None
    end_date_only = end.split('T')[0] if end else None

    events = []

    for user_id in selected_users:
        tasks = models.Task.objects.filter(
            managed_by_id=user_id,
        ).select_related('status', 'managed_by').values(
            'id', 'title', 'deadline', 'status__name',
            'managed_by_id',
            'managed_by__django_user__first_name',
            'managed_by__django_user__last_name'
        )

        for task in tasks:
            status = task['status__name']
            css_slug = status.replace(' ', '-').lower()

            user_name = f"{task['managed_by__django_user__first_name']} {task['managed_by__django_user__last_name']}"
            events.append({
                'id': str(task['id']),
                'title': f"{task['title']} ({user_name})",
                'start': task['deadline'].isoformat(),
                'end': task['deadline'].isoformat(),
                'status': task['status__name'],
                'className': 'status-' + css_slug,
                'user_id': str(task['managed_by_id']),
                'user_name': user_name
            })

        try:
            schedule = models.UserSchedule.objects.get(user_id=user_id)
        except models.UserSchedule.DoesNotExist:
            schedule = None

        if schedule and start_dt and end_dt:
            day = start_dt.date()
            end_day = end_dt.date()

            while day <= end_day:
                work_start = datetime.combine(day, schedule.work_hours_start)
                work_end = datetime.combine(day, schedule.work_hours_end)

                # до рабочего времени
                day_start = datetime.combine(day, time(0, 0))
                if day_start < work_start:
                    events.append({
                        'start': day_start.isoformat(),
                        'end': work_start.isoformat(),
                        'rendering': 'background',
                        'backgroundColor': '#1c1c1c',
                        'user_id': str(user_id),
                    })

                # после рабочего времени
                day_end = datetime.combine(day, time(23, 59, 59))
                if work_end < day_end:
                    events.append({
                        'start': work_end.isoformat(),
                        'end': day_end.isoformat(),
                        'rendering': 'background',
                        'backgroundColor': '#1c1c1c',
                        'user_id': str(user_id),
                    })

                personal_start = datetime.combine(day, schedule.personal_hours_start)
                personal_end = datetime.combine(day, schedule.personal_hours_end)
                events.append({
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
            events.append({
                'start': v.date_start.isoformat(),
                'end': (v.date_end + timedelta(days=1)).isoformat(),
                'rendering': 'background',
                'backgroundColor': '#363636',
                'user_id': str(user_id),
            })

            events.append({
                'start': datetime.combine(v.date_start, time(0, 0)).isoformat(),
                'end': datetime.combine(v.date_end, time(23, 59, 59)).isoformat(),
                'rendering': 'background',
                'backgroundColor': '#363636',
                'user_id': str(user_id),
            })

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
            tag = tag_form.save(commit=False)
            if not (tag.category or tag.subcategory or tag.for_what):
                tag = None
            else:
                tag.save()

            task = task_form.save(commit=False)
            task.created_by = custom_user
            task.status = models.Status.objects.get(name='new')
            task.tag = tag
            task.save()

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
            tag = tag_form.save()
            task = task_form.save(commit=False)

            if tag.category or tag.subcategory or tag.for_what:
                task.tag = tag
            else:
                task.tag = None

            task.save()

            messages.success(request, 'Task updated successfully')
            return redirect('index')

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
