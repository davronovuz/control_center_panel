from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('districts/', views.get_districts, name='get_districts'),
    path('mahallas/', views.get_mahallas, name='get_mahallas'),
    path('task/<uuid:pk>/auto-save/', views.task_auto_save, name='task_auto_save'),
    path('notifications/', views.get_notifications, name='get_notifications'),
]