from django.db import models
from django.contrib.auth.models import User, Group

class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telephone_number = models.CharField(max_length=15, default='88005553535')
    total_debt = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    def __str__(self):
        return self.user.username
