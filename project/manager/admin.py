from django.contrib import admin
from .models import CustomUser, Department, Holiday, Status, Tag, Task, Notification, UserSchedule, Vacation
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

User = get_user_model()

class CustomUserInline(admin.StackedInline):
    model = CustomUser
    can_delete = False

admin.site.unregister(User)

@admin.register(User)
class UserAdmin(UserAdmin):
    inlines = [CustomUserInline]

    list_filter = ('profile__department',)
    search_fields = ('username', 'email')
    list_display = ('username', 'email', 'first_name', 'last_name')

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ('name',)

@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_filter = ('department__name', 'date_time_start')
    search_fields = ('name',)

@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    search_fields = ('name',)

@admin.register(Tag)
class TagsAdmin(admin.ModelAdmin):
    list_display = ('category', 'subcategory', 'for_what')
    search_fields = ('category', 'subcategory', 'for_what')

@admin.register(Task)
class TasksAdmin(admin.ModelAdmin):
    search_fields = ('head_task__title', 'title')
    list_filter = ('status', 'priority')
    list_display = ('title', 'status', 'priority', 'deadline', 'assigned_by', 'managed_by')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Notification)
class NotificationsAdmin(admin.ModelAdmin):
    list_filter = ('type', 'send_time')
    list_display = ('message', 'type', 'send_time', 'get_task_title')

    #  description название колонки
    @admin.display(description="Task")
    def get_task_title(self, obj):
        return obj.task.title

@admin.register(UserSchedule)
class UserScheduleAdmin(admin.ModelAdmin):
    list_display = ('work_hours_start', 'work_hours_end', 'personal_hours_start', 'personal_hours_end', 'get_user')

    @admin.display(description="User")
    def get_user(self, obj):
        return obj.user.django_user.get_full_name()

@admin.register(Vacation)
class VacationAdmin(admin.ModelAdmin):
    list_display = ('date_start', 'date_end', 'tag', 'get_user')

    @admin.display(description="User")
    def get_user(self, obj):
        return obj.user_schedule.user.django_user.get_full_name()
