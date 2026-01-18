from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Admin
    path('', views.home, name='home'),
    path('statistics/', views.statistics, name='statistics'),

    # Leader
    path('leader/', views.leader_home, name='leader_home'),
    path('leader/tasks/', views.leader_tasks, name='leader_tasks'),
    path('leader/tasks/<uuid:pk>/', views.leader_task_detail, name='leader_task_detail'),
    path('leader/tasks/<uuid:pk>/submit/', views.leader_task_submit, name='leader_task_submit'),
]