from django.shortcuts import render


def orders(request):
    context = {
        'title': 'Orders',
    }
    return render(request, 'orders/orders.html', context)
