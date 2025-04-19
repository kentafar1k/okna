import random
import datetime
from django.core.management.base import BaseCommand, CommandError
from orders.models import Order
from clients.models import Client
from django.utils import timezone
from django.db.models import Q


class Command(BaseCommand):
    help = 'Добавление и удаление тестовых заказов с разными критериями'

    def add_arguments(self, parser):
        # Аргументы для добавления заказов
        parser.add_argument('--add', type=int, help='Количество заказов для добавления')
        parser.add_argument('--status', type=str, choices=['new', 'in_progress', 'ready', 'completed'], 
                            help='Статус заказов (new, in_progress, ready, completed)')
        parser.add_argument('--year', type=int, help='Год для новых заказов')
        parser.add_argument('--month', type=int, help='Месяц для новых заказов')
        
        # Аргументы для удаления заказов
        parser.add_argument('--delete', type=str, choices=['all', 'completed', 'test'], 
                          help='Удалить заказы (all - все, completed - завершенные, test - тестовые)')
        
        # Использовать тестовые номера заказов
        parser.add_argument('--test-prefix', type=str, default='ТЕСТ-', 
                          help='Префикс для тестовых заказов (по умолчанию "ТЕСТ-")')

    def handle(self, *args, **options):
        # Получаем аргументы
        add_count = options.get('add')
        status = options.get('status')
        year = options.get('year')
        month = options.get('month')
        delete_option = options.get('delete')
        test_prefix = options.get('test_prefix')
        
        # Если указан аргумент для удаления
        if delete_option:
            self._delete_orders(delete_option, test_prefix)
        
        # Если указан аргумент для добавления
        if add_count:
            # Проверяем, существуют ли клиенты
            if Client.objects.count() == 0:
                raise CommandError('Нет клиентов в базе данных. Сначала добавьте клиентов.')
            
            # Если не указан статус, используем случайный
            statuses = ['new', 'in_progress', 'ready', 'completed']
            if not status:
                status = None  # Будем выбирать случайно для каждого заказа
            
            # Создаем заказы
            self._add_orders(add_count, status, statuses, year, month, test_prefix)
    
    def _delete_orders(self, delete_option, test_prefix):
        if delete_option == 'all':
            count = Order.objects.count()
            Order.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'Удалено {count} заказов!'))
        
        elif delete_option == 'completed':
            count = Order.objects.filter(status='completed').count()
            Order.objects.filter(status='completed').delete()
            self.stdout.write(self.style.SUCCESS(f'Удалено {count} завершенных заказов!'))
        
        elif delete_option == 'test':
            count = Order.objects.filter(order_number__startswith=test_prefix).count()
            Order.objects.filter(order_number__startswith=test_prefix).delete()
            self.stdout.write(self.style.SUCCESS(f'Удалено {count} тестовых заказов!'))
    
    def _get_next_available_number(self, prefix, year, month):
        """Находит следующий доступный номер для заказа с учетом существующих номеров"""
        # Получаем существующие номера заказов с нужным префиксом, годом и месяцем
        year_month_pattern = f"{prefix}{year}-{month:02d}-"
        existing_orders = Order.objects.filter(order_number__startswith=year_month_pattern)
        
        if not existing_orders.exists():
            return f"{prefix}{year}-{month:02d}-001"
        
        # Находим максимальный номер
        max_number = 0
        for order in existing_orders:
            # Извлекаем числовую часть номера
            try:
                number_part = order.order_number.split('-')[-1]
                number = int(number_part)
                max_number = max(max_number, number)
            except (ValueError, IndexError):
                continue
        
        # Возвращаем следующий номер
        next_number = max_number + 1
        return f"{prefix}{year}-{month:02d}-{next_number:03d}"
    
    def _add_orders(self, count, status, statuses, year, month, test_prefix):
        # Получаем всех клиентов
        clients = list(Client.objects.all())
        
        # Текущий год и месяц, если не указаны
        current_year = timezone.now().year if not year else year
        current_month = timezone.now().month if not month else month
        
        # Генерируем случайные даты в указанном месяце
        start_date = datetime.date(current_year, current_month, 1)
        if current_month == 12:
            end_date = datetime.date(current_year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end_date = datetime.date(current_year, current_month + 1, 1) - datetime.timedelta(days=1)
        
        # Диапазон дней в месяце
        month_range = (end_date - start_date).days + 1
        
        # Создаем указанное количество заказов
        created_count = 0
        for i in range(count):
            try:
                # Выбираем случайного клиента
                client = random.choice(clients)
                
                # Генерируем случайную дату в указанном месяце
                random_day = random.randint(1, month_range)
                order_date = start_date + datetime.timedelta(days=random_day - 1)
                
                # Выбираем случайный статус, если не указан
                current_status = status if status else random.choice(statuses)
                
                # Генерируем случайную стоимость заказа (от 5000 до 50000)
                total_price = random.randint(5000, 50000)
                
                # Генерируем случайную предоплату (от 0 до 50% стоимости)
                prepayment = random.randint(0, int(total_price * 0.5))
                
                # Генерируем уникальный номер заказа с префиксом
                order_number = self._get_next_available_number(test_prefix, current_year, current_month)
                
                # Создаем заказ
                order = Order.objects.create(
                    client=client,
                    order_number=order_number,
                    start_date=order_date,
                    status=current_status,
                    total_price=total_price,
                    prepayment=prepayment
                )
                
                self.stdout.write(f"Создан заказ: {order_number}, Клиент: {client.full_name}, Статус: {current_status}, Сумма: {total_price} руб.")
                created_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Ошибка при создании заказа: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(f'Успешно добавлено {created_count} заказов!')) 