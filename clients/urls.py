from django.urls import path
from . import views

app_name = 'clients'

urlpatterns = [
    path('', views.client_list, name='client_list'),  # изменено с clients_list
    path('create/', views.client_create, name='client_create'),
    path('<int:client_id>/', views.client_detail, name='client_detail'),
    path('<int:client_id>/update/', views.client_update, name='client_update'),
] 