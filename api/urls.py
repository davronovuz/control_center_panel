from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('districts/', views.get_districts, name='get_districts'),
    path('mahallas/', views.get_mahallas, name='get_mahallas'),
    path('notifications/', views.get_notifications, name='get_notifications'),

    # Task API
    path('task/<uuid:pk>/auto-save/', views.task_auto_save, name='task_auto_save'),
    path('task/<uuid:pk>/excel-import/', views.task_excel_import, name='task_excel_import'),
    path('task/<uuid:pk>/excel-template/', views.task_excel_template, name='task_excel_template'),
    path('task/<uuid:pk>/delete-row/', views.task_delete_row, name='task_delete_row'),
]