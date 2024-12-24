from django.db import models
from clients.models import Client

class Order(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('glass_ordered', 'Glass Ordered'),
        ('assembly', 'Assembly in Progress'),
        ('ready', 'Ready for Pickup'),
        ('delivered', 'Delivered'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    order_number = models.CharField(max_length=20, unique=True)
    start_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    prepayment = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    payment_type = models.CharField(max_length=10, choices=[('cash', 'Cash'), ('transfer', 'Transfer')], default='cash')
    debt = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price =models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    # переопределение метода save(), который срабатывает при создании или обновлении записи в бд
    def save(self, *args, **kwargs):
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (x{self.quantity})"

