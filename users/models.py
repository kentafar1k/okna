from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('manager', 'Менеджер'),
        ('worker', 'Работник'),
        ('client', 'Клиент'),
    )
    
    user_type = models.CharField(
        max_length=10,
        choices=USER_TYPE_CHOICES,
        default='client',
        verbose_name='Тип пользователя'
    )

    def is_manager(self):
        return self.user_type == 'manager'

    def is_worker(self):
        return self.user_type == 'worker'

    def is_client(self):
        return self.user_type == 'client'

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username