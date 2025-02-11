from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=100, verbose_name='ФИО', default="-")
    phone = models.CharField(max_length=15, verbose_name='Телефон')
    email = models.EmailField(blank=True, null=True, verbose_name='Email', default="-")
    address = models.TextField(blank=True, null=True, verbose_name='Адрес', default="-")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'
        ordering = ['phone']

    def __str__(self):
        return self.full_name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('clients:client_detail', kwargs={'client_id': self.pk})

    def get_total_debt(self):
        """Возвращает общую сумму задолженности по всем заказам клиента"""
        total_debt = 0
        for order in self.order_set.all():
            debt = order.get_debt()
            if debt > 0:  # учитываем только положительные задолженности
                total_debt += debt
        return total_debt
