from django.db import models
from clients.models import Client
from django.utils import timezone
from django.core.validators import FileExtensionValidator

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
    pdf_file = models.FileField(
        upload_to='orders_pdf/',
        validators=[FileExtensionValidator(['pdf'])],
        verbose_name='PDF файл',
        blank=True,
        null=True,
        help_text='Загрузите PDF файл (необязательно)'
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
        # Если статус меняется на "completed", устанавливаем дату завершения
        if self.status == 'completed' and not self.completed_date:
            self.completed_date = timezone.now()
        # Если статус меняется с "completed" на другой, очищаем дату завершения
        elif self.status != 'completed':
            self.completed_date = None
        super().save(*args, **kwargs)

class Client(models.Model):
    # ... существующие поля ...

    def get_total_debt(self):
        """Возвращает общую сумму задолженности по всем заказам клиента"""
        total_debt = 0
        for order in self.order_set.all():
            debt = order.get_debt()
            if debt > 0:  # учитываем только положительные задолженности
                total_debt += debt
        return total_debt

