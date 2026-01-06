from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('leaders/', views.leader_list, name='leader_list'),
    path('leaders/create/', views.leader_create, name='leader_create'),
    path('leaders/<int:pk>/', views.leader_detail, name='leader_detail'),
    path('leaders/<int:pk>/edit/', views.leader_edit, name='leader_edit'),
    path('leaders/<int:pk>/delete/', views.leader_delete, name='leader_delete'),
]