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
from .models import OrderStatusHistory
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum, Q
import json


@manager_required
def orders(request):
    # Получаем параметры сортировки
    sort_by = request.GET.get('sort', 'uncompleted_first')  # По умолчанию сортируем по статусу (сначала новые)
    
    # Получаем год и месяц из GET-параметров или используем текущие
    year = request.GET.get('year', timezone.now().year)
    month = request.GET.get('month', timezone.now().month)
    
    try:
        year = int(year)
        month = int(month)
    except (ValueError, TypeError):
        year = timezone.now().year
        month = timezone.now().month
    
    # Базовый QuerySet
    orders_queryset = Order.objects.all()
    
    # Получаем параметр фильтрации по статусу (completed или активные)
    show_completed = request.GET.get('show_completed', 'false').lower() == 'true'
    
    # Фильтруем заказы по статусу
    if show_completed:
        orders_queryset = orders_queryset.filter(status='completed')
    else:
        orders_queryset = orders_queryset.exclude(status='completed')
    
    # Фильтруем заказы по году и месяцу
    monthly_orders = orders_queryset.filter(
        start_date__year=year,
        start_date__month=month
    )
    
    # Вычисляем сумму заказов за месяц
    monthly_total = sum(order.total_price for order in monthly_orders)
    
    # Получаем параметр поиска
    search_query = request.GET.get('search', '').strip()
    
    # Применяем фильтры поиска до сортировки
    if search_query:
        orders_queryset = orders_queryset.filter(
            order_number__icontains=search_query
        )
    
    # Обновляем логику сортировки
    sort_param = request.GET.get('sort', 'uncompleted_first')
    if sort_param == 'completed_first':
        # Кастомная сортировка: завершён -> готов -> в работе -> новый (и по дате)
        status_order = {'completed': 1, 'ready': 2, 'in_progress': 3, 'new': 4}
        orders_queryset = sorted(orders_queryset, key=lambda x: (status_order.get(x.status, 0), -x.start_date.timestamp()))
    elif sort_param == 'uncompleted_first':
        # Кастомная сортировка: новый -> в работе -> готов -> завершён (и по дате)
        status_order = {'new': 1, 'in_progress': 2, 'ready': 3, 'completed': 4}
        orders_queryset = sorted(orders_queryset, key=lambda x: (status_order.get(x.status, 0), -x.start_date.timestamp()))
    elif sort_param == 'start_date':
        orders_queryset = orders_queryset.order_by('start_date')
    else:  # '-start_date' по умолчанию
        orders_queryset = orders_queryset.order_by('-start_date')

    # Вычисляем общую задолженность (убираем проверку на положительное значение)
    total_debt = sum(order.get_debt() for order in orders_queryset)
    
    # Создаем список месяцев с их русскими названиями
    months = [(1, 'Январь'), (2, 'Февраль'), (3, 'Март'), (4, 'Апрель'),
              (5, 'Май'), (6, 'Июнь'), (7, 'Июль'), (8, 'Август'),
              (9, 'Сентябрь'), (10, 'Октябрь'), (11, 'Ноябрь'), (12, 'Декабрь')]
    
    # Словарь для удобного доступа к названиям месяцев
    month_names = dict(months)
    
    # Добавляем пагинацию только для завершённых заказов
    if show_completed:
        paginator = Paginator(orders_queryset, 20)  # Показываем 20 заказов на страницу
        page = request.GET.get('page')
        try:
            orders_paginated = paginator.page(page)
        except PageNotAnInteger:
            # Если страница не является целым числом, показываем первую страницу
            orders_paginated = paginator.page(1)
        except EmptyPage:
            # Если страница больше максимальной, показываем последнюю страницу
            orders_paginated = paginator.page(paginator.num_pages)
        
        orders_queryset = orders_paginated
    
    context = {
        'orders': orders_queryset,
        'search_query': search_query,
        'current_sort': sort_param,
        'total_debt': total_debt,
        'monthly_total': monthly_total,
        'selected_year': year,
        'selected_month': month,
        'years': range(timezone.now().year - 5, timezone.now().year + 1),
        'months': months,
        'month_names': month_names,
        'show_completed': show_completed,
        'is_paginated': show_completed and hasattr(orders_queryset, 'paginator'),
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
        
        # Получаем параметры сортировки
        sort_param = request.GET.get('sort', 'uncompleted_first')
        
        # Базовый QuerySet
        orders_queryset = Order.objects.filter(client=client)
        
        # Получаем параметр поиска
        search_query = request.GET.get('search', '').strip()
        
        # Применяем фильтры поиска до сортировки
        if search_query:
            orders_queryset = orders_queryset.filter(
                order_number__icontains=search_query
            )
        
        # Применяем сортировку (для QuerySet объектов)
        if sort_param == 'start_date':
            orders_queryset = orders_queryset.order_by('start_date')
        elif sort_param == '-start_date':
            orders_queryset = orders_queryset.order_by('-start_date')
        
        # Для кастомной сортировки сначала получаем список
        if sort_param in ['completed_first', 'uncompleted_first']:
            # Получаем список объектов
            orders_list = list(orders_queryset)
            
            # Применяем кастомную сортировку
            if sort_param == 'completed_first':
                # Кастомная сортировка: завершён -> готов -> в работе -> новый (и по дате)
                status_order = {'completed': 1, 'ready': 2, 'in_progress': 3, 'new': 4}
                orders_list = sorted(orders_list, key=lambda x: (status_order.get(x.status, 0), -x.start_date.timestamp()))
            else:  # 'uncompleted_first'
                # Кастомная сортировка: новый -> в работе -> готов -> завершён (и по дате)
                status_order = {'new': 1, 'in_progress': 2, 'ready': 3, 'completed': 4}
                orders_list = sorted(orders_list, key=lambda x: (status_order.get(x.status, 0), -x.start_date.timestamp()))
            
            # Вычисляем общую задолженность до пагинации
            total_debt = sum(order.get_debt() for order in orders_list)
            
            # Создаем пагинатор из отсортированного списка
            paginator = Paginator(orders_list, 20)  # Показываем 20 заказов на страницу
        else:
            # Вычисляем общую задолженность до пагинации
            total_debt = sum(order.get_debt() for order in orders_queryset)
            
            # Создаем пагинатор из QuerySet
            paginator = Paginator(orders_queryset, 20)  # Показываем 20 заказов на страницу
        
        # Получаем запрошенную страницу
        page = request.GET.get('page')
        try:
            orders = paginator.page(page)
        except PageNotAnInteger:
            # Если страница не является целым числом, показываем первую страницу
            orders = paginator.page(1)
        except EmptyPage:
            # Если страница больше максимальной, показываем последнюю страницу
            orders = paginator.page(paginator.num_pages)
        
    except Client.DoesNotExist:
        orders = []
        total_debt = 0
        messages.warning(request, 'Профиль клиента не найден')
    
    context = {
        'orders': orders,
        'is_client': True,
        'current_sort': sort_param,
        'total_debt': total_debt,
        'search_query': search_query,
        'is_paginated': hasattr(orders, 'paginator')
    }
    return render(request, 'orders/client_orders.html', context)

@worker_required
def worker_orders(request):
    # Получаем параметры сортировки
    sort_param = request.GET.get('sort', 'uncompleted_first')
    
    # Базовый QuerySet
    orders_queryset = Order.objects.all()
    
    # Получаем параметр фильтрации по статусу (completed или активные)
    show_completed = request.GET.get('show_completed', 'false').lower() == 'true'
    
    # Фильтруем заказы по статусу
    if show_completed:
        orders_queryset = orders_queryset.filter(status='completed')
    else:
        orders_queryset = orders_queryset.exclude(status='completed')
    
    # Получаем параметр поиска
    search_query = request.GET.get('search', '').strip()
    
    # Применяем фильтры поиска до сортировки
    if search_query:
        orders_queryset = orders_queryset.filter(
            order_number__icontains=search_query
        )
    
    # Применяем сортировку
    if sort_param == 'completed_first':
        # Кастомная сортировка: завершён -> готов -> в работе -> новый (и по дате)
        status_order = {'completed': 1, 'ready': 2, 'in_progress': 3, 'new': 4}
        orders_queryset = sorted(orders_queryset, key=lambda x: (status_order.get(x.status, 0), -x.start_date.timestamp()))
    elif sort_param == 'uncompleted_first':
        # Кастомная сортировка: новый -> в работе -> готов -> завершён (и по дате)
        status_order = {'new': 1, 'in_progress': 2, 'ready': 3, 'completed': 4}
        orders_queryset = sorted(orders_queryset, key=lambda x: (status_order.get(x.status, 0), -x.start_date.timestamp()))
    elif sort_param == 'start_date':
        orders_queryset = orders_queryset.order_by('start_date')
    else:  # '-start_date' по умолчанию
        orders_queryset = orders_queryset.order_by('-start_date')

    # Добавляем пагинацию только для завершённых заказов
    if show_completed:
        paginator = Paginator(orders_queryset, 20)  # Показываем 20 заказов на страницу
        page = request.GET.get('page')
        try:
            orders_paginated = paginator.page(page)
        except PageNotAnInteger:
            # Если страница не является целым числом, показываем первую страницу
            orders_paginated = paginator.page(1)
        except EmptyPage:
            # Если страница больше максимальной, показываем последнюю страницу
            orders_paginated = paginator.page(paginator.num_pages)
        
        orders_queryset = orders_paginated

    context = {
        'orders': orders_queryset,
        'search_query': search_query,
        'current_sort': sort_param,
        'is_worker': True,
        'show_completed': show_completed,
        'is_paginated': show_completed and hasattr(orders_queryset, 'paginator'),
    }
    return render(request, 'orders/worker_orders.html', context)

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

@require_POST
def update_status(request, order_id):
    """Обновление статуса заказа"""
    try:
        order = Order.objects.get(id=order_id)
        new_status = request.POST.get('status')
        
        if new_status in dict(Order.STATUS_CHOICES):
            # Сначала обновляем статус заказа
            order.status = new_status
            order.save()
            
            # Затем создаем запись в истории
            OrderStatusHistory.objects.create(
                order=order,
                status=new_status,
                created_at=timezone.now()
            )
            
            # Отправляем уведомления если нужно
            send_email = request.POST.get('send_email') == 'true'
            send_sms = request.POST.get('send_sms') == 'true'
            
            if new_status in ['ready', 'completed'] and (send_email or send_sms):
                try:
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
                        order_number = order.order_number
                        if len(order_number) > 5:
                            order_number = order_number[:5] + '..'
                        if not order_number[0].isdigit():
                            message = f"Ваш заказ \"{order_number}\" {status_message}"
                        else:
                            message = f"Ваш заказ №{order_number} {status_message}"
                        send_order_ready_sms(order.client.phone, order, message)

                except Exception as e:
                    # Логируем ошибку отправки уведомлений, но не прерываем обновление статуса
                    print(f"Ошибка отправки уведомлений: {str(e)}")
            
            # Если это запрос от работника и статус "completed", перенаправляем на страницу заказов
            if request.user.is_worker() and new_status == 'completed':
                return JsonResponse({
                    'success': True,
                    'message': f'Заказ №{order.order_number} отмечен как завершенный',
                    'redirect': reverse('orders:worker_orders')
                })
            
            return JsonResponse({
                'success': True,
                'message': 'Статус успешно обновлен',
                'new_status': new_status,
                'new_status_display': order.get_status_display()
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Недопустимый статус'
            }, status=400)
    except Order.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Заказ не найден'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

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
    
    # Получаем параметр сортировки
    sort_param = request.GET.get('sort', 'uncompleted_first')
    
    # Получаем параметр поиска
    search_query = request.GET.get('search', '').strip()
    
    # Базовый QuerySet
    orders = Order.objects.filter(client=client)
    
    # Применяем фильтры поиска до сортировки
    if search_query:
        orders = orders.filter(
            order_number__icontains=search_query
        )
    
    # Применяем сортировку
    if sort_param == 'completed_first':
        # Кастомная сортировка: завершён -> готов -> в работе -> новый (и по дате)
        status_order = {'completed': 1, 'ready': 2, 'in_progress': 3, 'new': 4}
        orders = sorted(orders, key=lambda x: (status_order.get(x.status, 0), -x.start_date.timestamp()))
    elif sort_param == 'uncompleted_first':
        # Кастомная сортировка: новый -> в работе -> готов -> завершён (и по дате)
        status_order = {'new': 1, 'in_progress': 2, 'ready': 3, 'completed': 4}
        orders = sorted(orders, key=lambda x: (status_order.get(x.status, 0), -x.start_date.timestamp()))
    elif sort_param == 'start_date':
        orders = orders.order_by('start_date')
    else:  # '-start_date' по умолчанию
        orders = orders.order_by('-start_date')
    
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
        'form': form,
        'current_sort': sort_param,
        'search_query': search_query
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
def update_order_number(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_number = request.POST.get('order_number', '').strip()
        
        if new_number:
            # Проверяем, не существует ли уже заказ с таким номером
            if Order.objects.filter(order_number=new_number).exclude(id=order_id).exists():
                messages.error(request, 'Заказ с таким номером уже существует')
            else:
                order.order_number = new_number
                order.save()
                messages.success(request, 'Номер заказа успешно обновлен')
        else:
            messages.error(request, 'Номер заказа не может быть пустым')
            
    return redirect('orders:order_detail', order_id=order_id)

@manager_required
def update_total_price(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        try:
            new_price = float(request.POST.get('total_price', 0))
            if new_price >= 0:
                order.total_price = new_price
                order.save()
                messages.success(request, 'Стоимость успешно обновлена')
            else:
                messages.error(request, 'Стоимость не может быть отрицательной')
        except ValueError:
            messages.error(request, 'Некорректное значение стоимости')
            
    return redirect('orders:order_detail', order_id=order_id)

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
@require_POST
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.delete()
    return JsonResponse({'success': True})

@manager_required
@require_POST
def delete_multiple_orders(request):
    try:
        data = json.loads(request.body)
        order_ids = data.get('order_ids', [])
        
        if not order_ids:
            return JsonResponse({'success': False, 'error': 'Не указаны ID заказов для удаления'})
        
        # Получаем все заказы одним запросом
        orders = Order.objects.filter(id__in=order_ids)
        
        # Проверяем, что все заказы существуют
        if len(orders) != len(order_ids):
            return JsonResponse({'success': False, 'error': 'Некоторые заказы не найдены'})
        
        # Удаляем все заказы
        orders.delete()
        
        return JsonResponse({'success': True})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Неверный формат данных'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

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
def update_file(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        if 'remove_file' in request.POST:
            # Удаляем старый файл
            if order.order_file:
                order.order_file.delete()
            messages.success(request, 'Файл заказа удален')
        elif 'order_file' in request.FILES:
            # Удаляем старый файл перед загрузкой нового
            if order.order_file:
                order.order_file.delete()
            # Сохраняем новый файл
            order.order_file = request.FILES['order_file']
            order.save()
            messages.success(request, 'Файл заказа обновлен')
        
    return redirect('orders:order_detail', order_id=order.id)

def get_order_status_history(request, order_id):
    """Получение истории статусов заказа"""
    try:
        order = Order.objects.get(id=order_id)
        history = OrderStatusHistory.objects.filter(order=order).order_by('-created_at')
        
        history_data = [{
            'status': item.status,
            'status_display': item.get_status_display(),
            'created_at': item.created_at.strftime('%d.%m.%Y %H:%M')
        } for item in history]
        
        return JsonResponse({
            'success': True,
            'history': history_data
        })
    except Order.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Заказ не найден'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@manager_required
def calculations(request):
    current_year = timezone.now().year
    years = range(current_year - 5, current_year + 1)
    
    selected_year = int(request.GET.get('year', current_year))
    selected_month = int(request.GET.get('month', timezone.now().month))
    
    # Список месяцев с их русскими названиями
    months = [(1, 'Январь'), (2, 'Февраль'), (3, 'Март'), (4, 'Апрель'),
              (5, 'Май'), (6, 'Июнь'), (7, 'Июль'), (8, 'Август'),
              (9, 'Сентябрь'), (10, 'Октябрь'), (11, 'Ноябрь'), (12, 'Декабрь')]
    
    # Словарь для удобного доступа к названиям месяцев
    month_names = dict(months)
    
    # Получаем все заказы за выбранный месяц и год
    orders = Order.objects.filter(
        start_date__year=selected_year,
        start_date__month=selected_month
    ).order_by('-start_date')
    
    # Считаем общую сумму заказов
    total_amount = sum(order.total_price for order in orders if order.total_price)
    
    # Вычисляем общую задолженность по всем заказам
    all_orders = Order.objects.all()
    total_debt = sum(order.get_debt() for order in all_orders)
    
    context = {
        'selected_year': selected_year,
        'selected_month': selected_month,
        'years': years,
        'months': months,
        'month_names': month_names,
        'total_amount': total_amount,
        'orders': orders,
        'total_debt': total_debt,
    }
    
    return render(request, 'orders/calculations.html', context)
