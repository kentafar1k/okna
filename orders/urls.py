from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.orders, name='orders'),  # для менеджера
    path('calculations/', views.calculations, name='calculations'),
    path('worker-orders/', views.worker_orders, name='worker_orders'),  # для работника
    path('my-orders/', views.client_orders, name='client_orders'),  # для клиента
    path('create/', views.create_order, name='create_order'),
    path('clients/', views.orders_client_list, name='clients'),
    path('clients/<int:client_id>/', views.orders_client_detail, name='client_detail'),
    path('<int:order_id>/', views.order_detail, name='order_detail'),
    path('<int:order_id>/update/', views.update_order, name='update_order'),
    path('<int:order_id>/update-status/', views.update_status, name='update_status'),
    path('<int:order_id>/update-prepayment/', views.update_prepayment, name='update_prepayment'),
    path('<int:order_id>/update-order-number/', views.update_order_number, name='update_order_number'),
    path('<int:order_id>/update-total-price/', views.update_total_price, name='update_total_price'),
    path('clients/add/', views.add_client, name='add_client'),
    path('profile/', views.client_profile, name='client_profile'),
    path('<int:order_id>/delete/', views.delete_order, name='delete_order'),
    path('delete-multiple/', views.delete_multiple_orders, name='delete_multiple_orders'),
    path('clients/delete/<int:client_id>/', views.delete_client, name='delete_client'),
    path('order/<int:order_id>/update-pdf/', views.update_file, name='update_file'),
    path('order/<int:order_id>/status-history/', views.get_order_status_history, name='order_status_history'),
]