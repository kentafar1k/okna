# Generated by Django 5.1.4 on 2024-12-26 12:19

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0002_client_telephone_number'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='client',
            options={'ordering': ['full_name'], 'verbose_name': 'Клиент', 'verbose_name_plural': 'Клиенты'},
        ),
        migrations.RemoveField(
            model_name='client',
            name='telephone_number',
        ),
        migrations.RemoveField(
            model_name='client',
            name='total_debt',
        ),
        migrations.RemoveField(
            model_name='client',
            name='user',
        ),
        migrations.AddField(
            model_name='client',
            name='address',
            field=models.TextField(blank=True, null=True, verbose_name='Адрес'),
        ),
        migrations.AddField(
            model_name='client',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='client',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True, verbose_name='Email'),
        ),
        migrations.AddField(
            model_name='client',
            name='full_name',
            field=models.CharField(default='Неизвестно', max_length=100, verbose_name='ФИО'),
        ),
        migrations.AddField(
            model_name='client',
            name='phone',
            field=models.CharField(default='Не указан', max_length=15, verbose_name='Телефон'),
        ),
        migrations.AddField(
            model_name='client',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
