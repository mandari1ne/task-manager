from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta, time, date
import os, json
from django.conf import settings
from django.core import mail
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from .models import (
    CustomUser, Department, Task, Status, Tag,
    UserSchedule, Vacation, default_deadline, Notification
)


class TaskModelTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="IT Department")
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        self.custom_user = CustomUser.objects.create(
            django_user=self.user,
            patronymic="Smith",
            department=self.department,
            job_title="Developer",
            telegram_username="@johndoe"
        )
        self.status = Status.objects.create(name="In Progress")
        self.tag = Tag.objects.create(
            category="Development",
            subcategory="Backend",
            for_what="API"
        )


class UserScheduleModelTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="HR Department")
        self.user = User.objects.create_user(
            username='scheduleuser',
            first_name='Alice',
            last_name='Johnson'
        )
        self.custom_user = CustomUser.objects.create(
            django_user=self.user,
            department=self.department,
            job_title="HR Manager",
            telegram_username="@alicej"
        )

    def test_user_schedule_creation(self):
        schedule = UserSchedule.objects.create(
            user=self.custom_user,
            work_hours_start=time(9, 0),
            work_hours_end=time(18, 0),
            personal_hours_start=time(19, 0),
            personal_hours_end=time(22, 0)
        )

        self.assertEqual(schedule.user, self.custom_user)
        self.assertEqual(schedule.work_hours_start, time(9, 0))
        self.assertEqual(schedule.work_hours_end, time(18, 0))
        self.assertEqual(schedule.personal_hours_start, time(19, 0))
        self.assertEqual(schedule.personal_hours_end, time(22, 0))

    def test_user_schedule_one_to_one_relationship(self):
        schedule = UserSchedule.objects.create(
            user=self.custom_user,
            work_hours_start=time(9, 0),
            work_hours_end=time(18, 0),
            personal_hours_start=time(19, 0),
            personal_hours_end=time(22, 0)
        )

        self.assertEqual(self.custom_user.schedule, schedule)


class VacationModelTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="Finance Department")
        self.user = User.objects.create_user(
            username='vacationuser',
            first_name='Bob',
            last_name='Brown'
        )
        self.custom_user = CustomUser.objects.create(
            django_user=self.user,
            department=self.department,
            job_title="Accountant",
            telegram_username="@bobb"
        )
        self.schedule = UserSchedule.objects.create(
            user=self.custom_user,
            work_hours_start=time(8, 0),
            work_hours_end=time(17, 0),
            personal_hours_start=time(18, 0),
            personal_hours_end=time(23, 0)
        )

    def test_vacation_creation(self):
        start_date = timezone.now().date() + timedelta(days=10)
        end_date = start_date + timedelta(days=14)

        vacation = Vacation.objects.create(
            user_schedule=self.schedule,
            date_start=start_date,
            date_end=end_date,
            tag="Annual Leave"
        )

        self.assertEqual(vacation.user_schedule, self.schedule)
        self.assertEqual(vacation.date_start, start_date)
        self.assertEqual(vacation.date_end, end_date)
        self.assertEqual(vacation.tag, "Annual Leave")

    def test_vacation_relationship_with_schedule(self):
        vacation = Vacation.objects.create(
            user_schedule=self.schedule,
            date_start=timezone.now().date() + timedelta(days=1),
            date_end=timezone.now().date() + timedelta(days=7),
            tag="Business Trip"
        )

        self.assertIn(vacation, self.schedule.vacations.all())


@override_settings(STATIC_ROOT=os.path.join(settings.BASE_DIR, "test_static"))
class ViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(
            username="user1", password="pass12345", first_name="John", last_name="Doe"
        )
        self.department = Department.objects.create(name="Test Department")

        self.profile = CustomUser.objects.create(
            django_user=self.user,
            department=self.department
        )

        self.client.login(username="user1", password="pass12345")

        self.status = Status.objects.create(name="new")
        self.task = Task.objects.create(
            title="Test Task",
            managed_by=self.profile,
            created_by=self.profile,
            status=self.status,
            deadline=datetime.now() + timedelta(days=1)
        )

        self.schedule = UserSchedule.objects.create(
            user=self.profile,
            work_hours_start=time(9, 0),
            work_hours_end=time(18, 0),
            personal_hours_start=time(13, 0),
            personal_hours_end=time(14, 0),
        )

    def test_profile_view_get(self):
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Profile")

    def test_change_password_valid(self):
        url = reverse("change_password")
        response = self.client.post(url, {
            "old_password": "pass12345",
            "new_password1": "newpass123",
            "new_password2": "newpass123",
        })

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])

        self.client.logout()
        self.assertTrue(self.client.login(username="user1", password="newpass123"))

    def test_edit_task_page(self):
        url = reverse("edit_task", args=[self.task.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Task")

    def test_delete_task(self):
        url = reverse("delete_task", args=[self.task.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertFalse(Task.objects.filter(id=self.task.id).exists())

class TaskSignalsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="sign_user",
            email="signal@test.com",
            password="12345"
        )
        self.custom_user = CustomUser.objects.create(
            django_user=self.user,
            department=Department.objects.create(name="Signals"),
        )
        self.tag = Tag.objects.create(
            category="Test",
            subcategory="Signal",
            for_what="Check"
        )
        self.status = Status.objects.create(name="new")

    def test_create_task_signal(self):
        mail.outbox = []

        task = Task.objects.create(
            title="Signal Create Test",
            managed_by=self.custom_user,
            created_by=self.custom_user,
            status=self.status,
            deadline=timezone.now() + timedelta(days=1),
            tag=self.tag,
        )

        self.assertEqual(Notification.objects.filter(task=task, type="Create").count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("was created", mail.outbox[0].body)

    def test_update_task_signal(self):
        task = Task.objects.create(
            title="Signal Update Test",
            managed_by=self.custom_user,
            created_by=self.custom_user,
            status=self.status,
            deadline=timezone.now() + timedelta(days=1),
            tag=self.tag,
        )

        mail.outbox = []

        task.title = "Updated Title"
        task.save()

        self.assertEqual(Notification.objects.filter(task=task, type="Update").count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("was updated", mail.outbox[0].body)

