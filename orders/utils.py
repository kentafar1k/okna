from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
import time
import requests
import base64  # библа для рассылки смс SMSAero

# login: cherald13377@yandex.ru
# pwd  : lfvpcnksiisuobmu

def send_order_ready_email(order):
    """Отправка email о готовности заказа"""
    if not order.client.email or order.client.email == '-':
        print(f"Email клиента отсутствует или равен '-': {order.client.email}")
        return False
        
    subject = f'Заказ №{order.order_number} готов'
    
    # Формируем HTML-версию письма
    html_message = render_to_string('orders/email/order_ready.html', {
        'order': order,
        'client': order.client
    })
    
    # Формируем текстовую версию письма
    plain_message = f"""
    Здравствуйте, {order.client.full_name}!
    
    Ваш заказ №{order.order_number} готов.
    
    Стоимость заказа: {order.total_price} ₽
    Внесенная предоплата: {order.prepayment or 0} ₽
    Остаток к оплате: {order.get_debt()} ₽
    
    С уважением,
    "Окна в мир"
    """
    
    try:
        # Добавляем небольшую задержку перед отправкой
        time.sleep(1)  # Задержка в 1 секунду
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[order.client.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"Письмо успешно отправлено на {order.client.email}")
        return True
    except Exception as e:
        print(f"Ошибка отправки email: {str(e)}")
        return False 

def send_order_ready_sms(order):
    """Отправка SMS о готовности заказа через SMSAero"""
    if not order.client.phone:
        print(f"Телефон клиента отсутствует")
        return False
        
    # Очищаем номер от лишних символов
    phone = ''.join(filter(str.isdigit, order.client.phone))
    
    # Формируем текст сообщения
    message = f"Здравствуйте! Ваш заказ №{order.order_number} готов. Остаток к оплате: {order.get_debt()} ₽"
    
    # Формируем заголовок авторизации
    auth_string = f"{settings.SMSAERO_EMAIL}:{settings.SMSAERO_API_KEY}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}'
    }
    
    # Параметры запроса
    params = {
        'number': phone,
        'text': message,
        'sign': 'SMS Aero'  # Подпись отправителя
    }
    
    try:
        response = requests.get(
            'https://gate.smsaero.ru/v2/sms/send',
            headers=headers,
            params=params
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"SMS успешно отправлено на номер +{phone}")
                return True
            else:
                print(f"Ошибка отправки SMS: {result.get('message', 'Неизвестная ошибка')}")
        else:
            print(f"Ошибка HTTP: {response.status_code}")
        return False
            
    except Exception as e:
        print(f"Ошибка отправки SMS: {str(e)}")
        return False 