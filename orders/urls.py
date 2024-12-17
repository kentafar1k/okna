from django.urls import path
from . import views


# from . import ?

app_name = 'orders'

urlpatterns = [
    path('', views.orders, name='orders'),
]