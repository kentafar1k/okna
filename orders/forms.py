from django import forms
from .models import Order
from clients.models import Client

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['client', 'order_number', 'total_price', 'prepayment', 'payment_type']
        widgets = {
            'client': forms.Select(attrs={
                'class': 'form-control',
            }),
            'order_number': forms.TextInput(attrs={'class': 'form-control'}),
            'total_price': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01', 'placeholder': 'Введите стоимость'}),
            'prepayment': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01', 'placeholder': 'Введите предоплату'}),
            'payment_type': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Изменяем отображение клиентов в выпадающем списке на их телефоны
        self.fields['client'].label = 'Телефон клиента'
        self.fields['client'].queryset = Client.objects.all().order_by('phone')
        self.fields['client'].widget.choices = [
            (client.id, f"{client.phone} ({client.full_name})") 
            for client in self.fields['client'].queryset
        ]
        self.fields['total_price'].label = 'Стоимость заказа'
        
        # Устанавливаем пустые начальные значения
        self.fields['total_price'].initial = None
        self.fields['prepayment'].initial = None