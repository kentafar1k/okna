from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Client

User = get_user_model()

class ClientCreateForm(forms.ModelForm):
    phone = forms.CharField(
        label='Телефон',
        widget=forms.TextInput(attrs={
            'placeholder': '+79999999999',
            'class': 'form-control'
        })
    )

    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'example@domain.com'
        }),
        required=False
    )

    full_name = forms.CharField(
        label='ФИО',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Иванов Иван Иванович'
        }),
        required=False
    )

    address = forms.CharField(
        label='Адрес',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Введите адрес'
        }),
        required=False
    )

    class Meta:
        model = Client
        fields = ['phone', 'full_name', 'email']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@mail.com'})
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        # Очищаем номер от всех символов кроме цифр
        cleaned_phone = ''.join(filter(str.isdigit, phone))
        
        # Проверяем длину номера
        if len(cleaned_phone) != 11:
            raise forms.ValidationError('Номер телефона должен содержать 11 цифр')
        
        # Проверяем уникальность номера
        if Client.objects.filter(phone=cleaned_phone).exists():
            raise forms.ValidationError('Клиент с таким номером телефона уже существует')
        
        return cleaned_phone

    def save(self, commit=True):
        client = super().save(commit=False)
        
        # Создаем пользователя с номером телефона в качестве пароля
        user = User.objects.create_user(
            username=client.phone,
            password=client.phone,  # Используем номер телефона как пароль
            user_type='client'
        )
        
        client.user = user
        
        if commit:
            client.save()
        
        return client


class ClientUpdateForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['full_name', 'phone', 'email', 'address']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
        } 