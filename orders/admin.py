from django.contrib import admin

from .models import Order, OrderItem



class OrderItemInline(admin.TabularInline):

    model = OrderItem

    extra = 1



@admin.register(Order)

class OrderAdmin(admin.ModelAdmin):

    list_display = ['order_number', 'client', 'start_date', 'status', 'total_price']

    list_filter = ['status', 'start_date']

    search_fields = ['order_number', 'client__full_name']

    inlines = [OrderItemInline]



# Не регистрируем OrderItem отдельно, так как он будет отображаться внутри Order

# admin.site.register(OrderItem)  # Удалите эту строку, если она есть
