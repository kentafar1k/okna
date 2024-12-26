from django.shortcuts import render
from .models import Order


def orders(request):
    # Получаем все активные заказы, сортируем по дате (новые сверху)
    active_orders = Order.objects.exclude(status='delivered').order_by('-start_date')

    # Добавляем поиск по номеру заказа, если есть параметр search в запросе
    search_query = request.GET.get('search', '')
    if search_query:
        active_orders = active_orders.filter(order_number__icontains=search_query)

    context = {
        'title': 'Orders',
        'orders': active_orders,
    }
    return render(request, 'orders/orders.html', context)
