from django.urls import path
from . import api, views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('api_holiday/', api.HolidayApiView.as_view(), name='api_holiday'),
    path('api_test_hol/', api.get_holiday, name='get_holiday'),
    path('api_post_task/', api.post_task, name='post_task'),
    path('', views.IndexView.as_view()),
    path('tasks/', views.get_tasks, name='tasks'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('change_password/', views.change_password, name='change_password'),
    path('personal_time/', views.get_personal_time, name='personal_time'),
]
