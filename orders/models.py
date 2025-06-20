from django.db import models
from clients.models import Client
from django.utils import timezone
from django.core.validators import FileExtensionValidator
import os

class Order(models.Model):
    STATUS_CHOICES = (
        ('new', 'Новый'),
        ('in_progress', 'В работе'),
        ('ready', 'Готов'),
        ('completed', 'Завершён')
    )
    
    PAYMENT_CHOICES = (
        ('cash', 'Наличные'),
        ('card', 'Карта'),
        ('transfer', 'Перевод')
    )

    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name='Клиент')
    order_number = models.CharField(max_length=50, unique=True, verbose_name='Номер заказа')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name='Статус')
    start_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Общая стоимость')
    prepayment = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Предоплата')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='cash', verbose_name='Тип оплаты')
    completed_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата завершения')
    order_file = models.FileField(
        upload_to='orders_files/',
        validators=[FileExtensionValidator(['pdf', 'xlsx', 'xls', 'doc', 'docx'])],
        verbose_name='Файл заказа',
        blank=True,
        null=True,
        help_text='Загрузите файл заказа (PDF, Excel, Word)'
    )

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-start_date']

    def __str__(self):
        return f'Заказ №{self.order_number}'

    def get_debt(self):
        """Возвращает сумму задолженности по заказу"""
        return self.total_price - (self.prepayment or 0)

    def save(self, *args, **kwargs):
        # Если это новый заказ (нет id)
        if not self.id:
            # Сначала сохраняем заказ, чтобы получить id
            super().save(*args, **kwargs)
            
            # Создаем запись в истории статусов
            OrderStatusHistory.objects.create(
                order=self,
                status='new',
                created_at=timezone.now()
            )
        else:
            # Если статус меняется на "completed", устанавливаем дату завершения
            if self.status == 'completed' and not self.completed_date:
                self.completed_date = timezone.now()
            # Если статус меняется с "completed" на другой, очищаем дату завершения
            elif self.status != 'completed':
                self.completed_date = None
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Удаляем файл заказа, если он существует
        if self.order_file:
            # Получаем путь к файлу
            file_path = self.order_file.path
            # Проверяем существование файла
            if os.path.isfile(file_path):
                # Удаляем файл
                os.remove(file_path)
        # Вызываем родительский метод delete
        super().delete(*args, **kwargs)

def get_total_debt(self):
    """Возвращает общую сумму задолженности по всем заказам клиента"""
    total_debt = 0
    for order in self.order_set.all():
        debt = order.get_debt()
        total_debt += debt  # Убираем проверку на положительное значение
    return total_debt

# Добавляем метод к модели Client
Client.get_total_debt = get_total_debt

class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order.order_number} - {self.get_status_display()} ({self.created_at})"

