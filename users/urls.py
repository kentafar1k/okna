from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'users'

urlpatterns = [
    path('', views.login_view, name='login'),  # корневой URL для логина
    path('logout/', views.logout_view, name='logout'),
]