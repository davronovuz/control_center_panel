from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),

    # Leaders
    path('leaders/', views.leader_list, name='leader_list'),
    path('leaders/create/', views.leader_create, name='leader_create'),
    path('leaders/<uuid:pk>/', views.leader_detail, name='leader_detail'),
    path('leaders/<uuid:pk>/edit/', views.leader_edit, name='leader_edit'),
    path('leaders/<uuid:pk>/delete/', views.leader_delete, name='leader_delete'),

    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<uuid:pk>/read/', views.notification_read, name='notification_read'),
    path('notifications/mark-all-read/', views.notifications_mark_all_read, name='notifications_mark_all_read'),
]