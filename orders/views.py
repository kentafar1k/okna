from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Order
from users.decorators import manager_required, worker_required, client_required
from .forms import OrderForm
from django.contrib import messages
from clients.models import Client
from django.http import JsonResponse
from clients.forms import ClientCreateForm, ClientUpdateForm
from django.urls import reverse
from django.db import models
from .utils import send_order_ready_email, send_order_ready_sms


@manager_required
def orders(request):
    # Получаем параметры сортировки
    sort_by = request.GET.get('sort', '-start_date')  # По умолчанию сортируем по дате (новые сверху)
    
    # Базовый QuerySet
    orders_queryset = Order.objects.all()
    
    # Обновляем логику сортировки
    sort_param = request.GET.get('sort', '-start_date')
    if sort_param == 'completed_first':
        orders_queryset = orders_queryset.order_by('status', '-start_date')  # Сначала незавершенные
    elif sort_param == 'uncompleted_first':
        orders_queryset = orders_queryset.order_by('-status', '-start_date')   # Сначала завершенные
    elif sort_param == 'start_date':
        orders_queryset = orders_queryset.order_by('start_date')
    else:  # '-start_date' по умолчанию
        orders_queryset = orders_queryset.order_by('-start_date')

    # Получаем параметр поиска
    search_query = request.GET.get('search', '').strip()
    
    if search_query:
        # Применяем фильтры поиска
        orders_queryset = orders_queryset.filter(
            order_number__icontains=search_query
        )

    # Вычисляем общую задолженность (убираем проверку на положительное значение)
    total_debt = sum(order.get_debt() for order in orders_queryset)
    
    context = {
        'orders': orders_queryset,
        'search_query': search_query,
        'current_sort': sort_param,
        'total_debt': total_debt,
    }
    return render(request, 'orders/orders.html', context)

@manager_required
def create_order(request):
    # Определяем, откуда пришел запрос
    return_url = 'orders:orders'  # По умолчанию возвращаемся к списку заказов
    
    if request.method == 'POST':
        form = OrderForm(request.POST, request.FILES)
        if form.is_valid():
            order = form.save(commit=False)
            order.status = 'new'
            order.save()
            messages.success(request, 'Заказ успешно создан')
            return redirect('orders:orders')
        else:
            messages.error(request, 'Пожалуйста, проверьте введенные данные')
    else:
        # Получаем ID клиента из GET-параметров
        client_id = request.GET.get('client')
        if client_id:
            try:
                client = Client.objects.get(id=client_id)
                form = OrderForm(initial={'client': client})
                return_url = 'orders:clients'  # Если пришли со страницы клиентов
            except Client.DoesNotExist:
                form = OrderForm()
        else:
            form = OrderForm()
    
    return render(request, 'orders/create_order.html', {
        'form': form,
        'return_url': return_url
    })

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    template = 'orders/order_detail.html'
    context = {'order': order}
    
    # Проверяем права доступа
    if request.user.is_client():
        # Клиенты могут видеть только свои заказы
        if order.client.user != request.user:
            messages.error(request, 'У вас нет доступа к этому заказу')
            return redirect('orders:client_orders')
    elif request.user.is_worker():
        # Работники видят специальный шаблон
        template = 'orders/worker_order_detail.html'
    elif not (request.user.is_staff or request.user.is_superuser or request.user.is_manager()):
        # Если пользователь не имеет нужных прав
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('users:login')
    
    return render(request, template, context)

@manager_required
def update_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            return redirect('orders:order_detail', order_id=order.id)
    else:
        form = OrderForm(instance=order)
    return render(request, 'orders/update_order.html', {'form': form, 'order': order})

@client_required
def client_orders(request):
    try:
        # Получаем клиента, связанного с текущим пользователем
        client = Client.objects.get(user=request.user)
        # Получаем все заказы клиента, сортируем по дате (новые сверху)
        orders = Order.objects.filter(client=client).order_by('-start_date')
    except Client.DoesNotExist:
        orders = Order.objects.none()
        messages.warning(request, 'Профиль клиента не найден')
    
    context = {
        'orders': orders,
        'is_client': True  # флаг для шаблона
    }
    return render(request, 'orders/client_orders.html', context)

@worker_required
def worker_orders(request):
    # Показываем все незавершенные заказы для работника
    orders_queryset = Order.objects.exclude(status='completed').order_by('-start_date')

    # Получаем параметр поиска
    search_query = request.GET.get('search', '').strip()
    
    if search_query:
        orders_queryset = orders_queryset.filter(
            order_number__icontains=search_query
        )

    context = {
        'orders': orders_queryset,
        'search_query': search_query,
        'is_worker': True  # флаг для шаблона
    }
    return render(request, 'orders/worker_orders.html', context)

@manager_required
def worker_update_status(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            
            # Если заказ завершен, показываем сообщение
            if new_status == 'completed':
                messages.success(request, f'Заказ №{order.order_number} отмечен как завершенный')
                return JsonResponse({'success': True, 'redirect': reverse('orders:worker_orders')})
            
            return JsonResponse({'success': True})
    return JsonResponse({'success': False})

@manager_required
def clients_view(request):
    # Базовый queryset
    clients_queryset = Client.objects.all().order_by('full_name')
    
    # Получаем параметр поиска
    search_query = request.GET.get('search', '').strip()
    
    if search_query:
        # Применяем фильтр поиска по имени
        clients_queryset = clients_queryset.filter(
            full_name__icontains=search_query
        )
    
    context = {
        'clients': clients_queryset,
        'search_query': search_query,
    }
    return render(request, 'orders/clients.html', context)

@manager_required
def update_status(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')
        send_email = request.POST.get('send_email') == 'true'
        send_sms = request.POST.get('send_sms') == 'true'

        # Сохраняем предыдущий статус
        old_status = order.status
        
        # Обновляем статус
        order.status = new_status
        order.save()

        # Отправляем уведомления только если статус изменился на 'ready' или 'completed'
        if (new_status in ['ready', 'completed']) and (old_status != new_status):
            # Определяем текст сообщения в зависимости от статуса
            status_message = "готов" if new_status == 'ready' else "отгружен"
            message = f"Ваш заказ №{order.order_number} {status_message}"
            
            if send_email:
                send_order_ready_email(
                    email=order.client.email,
                    order_number=order.order_number,
                    message=message,
                    total_price=order.total_price,
                    prepayment=order.prepayment or 0,
                    debt=order.get_debt()
                )
            
            if send_sms:
                sms_message = f"{message}. Остаток к оплате: {order.get_debt()} ₽"
                send_order_ready_sms(order.client.phone, order.order_number, sms_message)

        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})

@manager_required
def add_client(request):
    # Получаем параметр return_to из GET или сохраняем из реферера при POST
    return_to = request.GET.get('return_to') or request.POST.get('return_to') or request.META.get('HTTP_REFERER', '')
    
    if request.method == 'POST':
        form = ClientCreateForm(request.POST)
        if form.is_valid():
            try:
                client = form.save()
                messages.success(request, f'Клиент {client.full_name} успешно добавлен')
                # Если return_to содержит create_order, перенаправляем на создание заказа с client_id
                if 'create_order' in return_to:
                    return redirect(f"{reverse('orders:create_order')}?client={client.id}")
                return redirect('orders:clients')
            except Exception as e:
                messages.error(request, f'Ошибка при создании клиента: {str(e)}')
        else:
            # Выводим ошибки формы
            for field in form:
                for error in field.errors:
                    messages.error(request, f'Ошибка в поле {field.label}: {error}')
    else:
        form = ClientCreateForm()
    
    return render(request, 'orders/add_client.html', {
        'form': form,
        'return_to': return_to
    })

@manager_required
def orders_client_list(request):
    """Представление списка клиентов в контексте заказов"""
    # Получаем параметры сортировки
    sort_by = request.GET.get('sort', '-last_order')  # По умолчанию сортируем по дате последнего заказа
    
    # Базовый QuerySet с аннотацией даты последнего заказа
    clients = Client.objects.annotate(
        last_order_date=models.Max('order__start_date')
    )
    
    # Применяем сортировку
    if sort_by == '-last_order':
        clients = clients.order_by(models.F('last_order_date').desc(nulls_last=True))
    elif sort_by == 'last_order':
        clients = clients.order_by(models.F('last_order_date').asc(nulls_last=True))
    
    # Поиск
    search_query = request.GET.get('search', '').strip()
    if search_query:
        clients = clients.filter(
            models.Q(full_name__icontains=search_query) |
            models.Q(phone__icontains=search_query)
        )
    
    context = {
        'clients': clients,
        'orders_context': True,
        'search_query': search_query,
        'current_sort': sort_by
    }
    return render(request, 'orders/clients.html', context)

@manager_required
def orders_client_detail(request, client_id):
    """Детали клиента в контексте заказов"""
    client = get_object_or_404(Client, id=client_id)
    orders = Order.objects.filter(client=client).order_by('-start_date')
    
    if request.method == 'POST':
        form = ClientUpdateForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, 'Данные клиента успешно обновлены')
            return redirect('orders:client_detail', client_id=client.id)
    else:
        form = ClientUpdateForm(instance=client)
    
    return render(request, 'orders/client_detail.html', {
        'client': client,
        'orders': orders,
        'form': form
    })


@client_required
def client_profile(request):
    try:
        client = Client.objects.get(user=request.user)
    except Client.DoesNotExist:
        messages.error(request, 'Профиль клиента не найден')
        return redirect('orders:client_orders')

    if request.method == 'POST':
        form = ClientUpdateForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлен')
            return redirect('orders:client_profile')
    else:
        form = ClientUpdateForm(instance=client)

    return render(request, 'orders/client_profile.html', {
        'form': form,
        'client': client
    })

@manager_required
def update_prepayment(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        try:
            new_prepayment = float(request.POST.get('prepayment', 0))
            order.prepayment = new_prepayment
            order.save()
            messages.success(request, 'Предоплата успешно обновлена')
        except ValueError:
            messages.error(request, 'Некорректное значение предоплаты')
    return redirect('orders:order_detail', order_id=order.id)

@manager_required
def delete_order(request, order_id):
    if request.method == 'POST':
        try:
            order = Order.objects.get(id=order_id)
            order.delete()
            return JsonResponse({'success': True})
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Заказ не найден'})
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@manager_required
def delete_client(request, client_id):
    if request.method == 'POST':
        try:
            client = Client.objects.get(id=client_id)
            client.delete()  # Это также удалит все связанные заказы из-за CASCADE
            return JsonResponse({'success': True})
        except Client.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Клиент не найден'})
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@manager_required
def update_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        if 'remove_pdf' in request.POST:
            # Удаляем старый файл
            if order.pdf_file:
                order.pdf_file.delete()
            messages.success(request, 'PDF файл удален')
        elif 'pdf_file' in request.FILES:
            # Удаляем старый файл перед загрузкой нового
            if order.pdf_file:
                order.pdf_file.delete()
            # Сохраняем новый файл
            order.pdf_file = request.FILES['pdf_file']
            order.save()
            messages.success(request, 'PDF файл обновлен')
        
    return redirect('orders:order_detail', order_id=order.id)
