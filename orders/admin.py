from django.contrib import admin
from .models import Order

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'client', 'start_date', 'status', 'total_price']
    list_filter = ['status', 'start_date']
    search_fields = ['order_number', 'client__full_name']
