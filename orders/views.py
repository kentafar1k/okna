from django.shortcuts import render
from django.views.generic import ListView
from .models import Order

class OrderListView(ListView):
    model = Order
    template_name = 'orders/orders.html'
    context_object_name = 'orders'
    
    def get_queryset(self):
        # Получаем все заказы, сортируем по дате (новые сверху)
        # Исключаем заказы со статусом 'delivered'
        return Order.objects.exclude(status='delivered').order_by('-start_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Здесь можно добавить дополнительные данные в контекст
        return context

def clients_list_view(request):
    context = {
        'title': 'Clients',
    }
    return render(request, 'orders/clients.html', context)
