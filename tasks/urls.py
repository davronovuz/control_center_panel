from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    path('', views.task_list, name='task_list'),
    path('create/', views.task_create, name='task_create'),
    path('<uuid:pk>/', views.task_detail, name='task_detail'),
    path('<uuid:pk>/edit/', views.task_edit, name='task_edit'),
    path('<uuid:pk>/delete/', views.task_delete, name='task_delete'),
    path('<uuid:pk>/publish/', views.task_publish, name='task_publish'),
    path('<uuid:pk>/results/', views.task_results, name='task_results'),
    path('<uuid:pk>/export/', views.task_export, name='task_export'),
]