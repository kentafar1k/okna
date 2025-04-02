from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
import time
import requests
import base64  # библа для рассылки смс SMSAero

# login: cherald13377@yandex.ru
# pwd  : lfvpcnksiisuobmu

def send_order_ready_email(email, order_number, message, total_price=None, prepayment=None, debt=None):
    """Отправка email о готовности заказа"""
    if not email or email == '-':
        print(f"Email клиента отсутствует или равен '-': {email}")
        return False
        
    subject = f'Информация о заказе №{order_number}'
    
    # Подготавливаем контекст для шаблона
    context = {
        'order_number': order_number,
        'message': message,
        'total_price': total_price,
        'prepayment': prepayment,
        'debt': debt
    }
    
    # Рендерим HTML шаблон
    html_message = render_to_string('orders/email/order_ready.html', context)
    
    # Формируем текстовую версию письма
    plain_message = f"""
    Здравствуйте!
    
    {message}
    
    Номер вашего заказа: {order_number}
    Стоимость заказа: {total_price} ₽
    Внесенная предоплата: {prepayment} ₽
    Остаток к оплате: {debt} ₽
    
    С уважением,
    "Окна в мир"
    """
    
    try:
        # Добавляем небольшую задержку перед отправкой
        time.sleep(1)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"Письмо успешно отправлено на {email}")
        return True
    except Exception as e:
        print(f"Ошибка отправки email: {str(e)}")
        return False

def send_order_ready_sms(phone, order_number, message):
    """Отправка SMS о готовности заказа через SMSAero"""
    if not phone:
        print(f"Телефон клиента отсутствует")
        return False
        
    # Очищаем номер от лишних символов
    phone = ''.join(filter(str.isdigit, phone))

    debt = str(int(float(order_number.get_debt())))  # Remove decimal point and trailing zeros
    
    # Формируем текст сообщения
    sms_text = (
        f'{message}\n'
        f'Остаток к оплате: {debt}₽\n'  # Use the modified debt variable
        f'"Окна в мир"'
    )
    
    # Формируем заголовок авторизации
    auth_string = f"{settings.SMSAERO_EMAIL}:{settings.SMSAERO_API_KEY}"
    auth_header = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_header}'
    }
    
    # Параметры запроса
    params = {
        'number': phone,
        'text': sms_text,
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