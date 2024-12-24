from django.contrib.auth.models import AbstractUser
from django.db import models

# class CustomUser(AbstractUser):
#     role = models.CharField(max_length=20, choices=[
#         ('admin', 'Admin'),
#         ('manager', 'Manager'),
#         ('employee', 'Employee'),
#     ], default='employee')

class User(AbstractUser):
    role = models.CharField(max_length=20, choices=[
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('employee', 'Employee'),
    ], default='employee')

    class Meta:
        db_table = 'users_customuser'