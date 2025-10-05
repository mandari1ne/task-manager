from django.urls import path
from . import api, views

urlpatterns = [
    path('api_holiday/', api.HolidayApiView.as_view(), name='api_holiday'),
    path('api_test_hol/', api.get_holiday, name='get_holiday'),
    path('api_post_task/', api.post_task, name='post_task'),
    path('', views.IndexView.as_view()),
    path('tasks/', views.get_tasks, name='tasks'),
]
