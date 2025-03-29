from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from django.conf import settings
from clients.models import Client
from orders.models import Order
from asgiref.sync import sync_to_async

# Состояния разговора
PHONE = 0

class OrderBot:
    def __init__(self):
        self.application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        
        # Добавляем обработчики
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                PHONE: [
                    MessageHandler(filters.CONTACT, self.get_orders_by_contact),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_orders_by_text)
                ],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )
        
        self.application.add_handler(conv_handler)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет приветственное сообщение и клавиатуру с командами"""
        keyboard = [
            ['📱 Ввести номер телефона', '📍 Узнать геопозицию']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            'Здравствуйте, мы компания "Окна в мир"! У этого бота вы можете узнать информацию о своих заказах по номеру телефона или посмотреть нашу геопозицию. Выберите действие:',
            reply_markup=reply_markup
        )
        return PHONE

    @sync_to_async
    def get_client_orders(self, phone):
        """Получение заказов клиента по номеру телефона"""
        try:
            clean_phone = ''.join(filter(str.isdigit, phone))
            
            if len(clean_phone) == 11:
                print(f"Ищем клиента с номером: {clean_phone}")
                
                try:
                    client = Client.objects.get(phone=clean_phone)
                    orders = list(Order.objects.filter(client=client).order_by('-start_date'))
                    return client, orders
                except Client.DoesNotExist:
                    if clean_phone.startswith('7') or clean_phone.startswith('8'):
                        alt_phone = clean_phone[1:]
                        print(f"Пробуем альтернативный номер: {alt_phone}")
                        try:
                            client = Client.objects.get(phone=alt_phone)
                            orders = list(Order.objects.filter(client=client).order_by('-start_date'))
                            return client, orders
                        except Client.DoesNotExist:
                            pass
            
            print(f"Клиент не найден. Очищенный номер: {clean_phone}")
            return None, None
        except Exception as e:
            print(f"Ошибка при поиске клиента: {str(e)}")
            return None, None

    async def get_orders_by_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка полученного контакта"""
        phone = update.message.contact.phone_number
        # Форматируем номер телефона
        if phone.startswith('+'):
            phone = phone[1:]
        elif phone.startswith('8'):
            phone = '7' + phone[1:]
        elif phone.startswith('7'):
            phone = phone
        else:
            phone = '7' + phone

        # Ищем клиента по номеру телефона
        client = await self.get_client_by_phone(phone)
        
        if client:
            # Получаем активные заказы клиента
            orders = await self.get_active_orders(client)
            
            if orders:
                # Создаем клавиатуру с активными заказами
                keyboard = []
                for order in orders:
                    status_emoji = {
                        'new': '📝',
                        'in_progress': '⚙️',
                        'ready': '✅'
                    }.get(order.status, '')
                    keyboard.append([f'{status_emoji} Заказ №{order.order_number}'])
                keyboard.extend([
                    ['📍 Узнать геопозицию'],
                    ['🔙 Вернуться назад']
                ])
                
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text(
                    f'Найдены ваши заказы. Выберите заказ для просмотра информации:\n'
                    f'📝 - новые заказы\n'
                    f'⚙️ - заказы в работе\n'
                    f'✅ - готовые заказы',
                    reply_markup=reply_markup
                )
                return PHONE
            else:
                keyboard = [
                    ['📍 Узнать геопозицию'],
                    ['🔙 Вернуться назад']
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text(
                    f'У вас нет заказов.',
                    reply_markup=reply_markup
                )
                return PHONE
        else:
            keyboard = [
                ['📍 Узнать геопозицию'],
                ['🔙 Вернуться назад']
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                'Клиент с таким номером телефона не найден.',
                reply_markup=reply_markup
            )
            return PHONE

    async def get_orders_by_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстового сообщения"""
        text = update.message.text
        
        if text == '📍 Узнать геопозицию':
            # Отправляем геопозицию базы
            await self.application.bot.send_location(
                chat_id=update.effective_chat.id,
                latitude=59.196899,
                longitude=39.803727
            )
            await update.message.reply_text(
                'Мы находимся по адресу:\n'
                'ул. Гагарина 88в, бокс 101'
            )
            
            # Возвращаем пользователя к предыдущему состоянию с активными заказами
            if hasattr(context, 'user_data') and 'last_client' in context.user_data:
                client = context.user_data['last_client']
                active_orders = await self.get_active_orders(client)
                keyboard = []
                for order in active_orders:
                    status_emoji = {
                        'new': '📝',
                        'in_progress': '⚙️',
                        'ready': '✅'
                    }.get(order.status, '')
                    keyboard.append([f'{status_emoji} Заказ №{order.order_number}'])
                keyboard.extend([
                    ['📍 Узнать геопозицию'],
                    ['🔙 Вернуться назад']
                ])
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text(
                    'Выберите заказ для просмотра информации:',
                    reply_markup=reply_markup
                )
            return PHONE
        elif text == '📱 Ввести номер телефона':
            # Создаем клавиатуру с кнопкой отправки контакта
            keyboard = [
                [KeyboardButton("📱 Отправить мой номер", request_contact=True)],
                ['🔙 Вернуться назад']
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                'Пожалуйста, отправьте ваш номер телефона одним из способов:\n'
                '1. Нажмите кнопку "Отправить мой номер"\n'
                '2. Или введите номер вручную в формате +7XXXXXXXXXX',
                reply_markup=reply_markup
            )
            return PHONE
        elif text == '🔙 Вернуться назад':
            return await self.start(update, context)
        elif text.startswith('Заказ №') or text.startswith('✅ Заказ №') or text.startswith('⚙️ Заказ №') or text.startswith('📝 Заказ №'):
            # Обработка нажатия на кнопку заказа
            order_number = text.split('№')[1].strip()
            order = await self.get_order_by_number(order_number)
            
            if order:
                # Получаем клиента из заказа
                client = await self.get_order_client(order)
                # Сохраняем клиента в контексте
                context.user_data['last_client'] = client
                # Получаем общую задолженность клиента
                total_debt = await self.get_client_total_debt(client)
                
                # Показываем информацию о заказе
                message = (
                    f'Информация о заказе №{order.order_number}:\n\n'
                    f'Статус: {order.get_status_display()}\n'
                    f'Дата создания: {order.start_date.strftime("%d.%m.%Y")}\n'
                    f'Стоимость: {order.total_price} ₽\n'
                    f'Предоплата: {order.prepayment or 0} ₽\n'
                    f'Задолженность: {order.get_debt()} ₽\n\n'
                    f'Общая задолженность: {total_debt} ₽'
                )
                await update.message.reply_text(message)
                
                # Получаем активные заказы клиента для обновления панели
                active_orders = await self.get_active_orders(client)
                
                # Создаем обновленную клавиатуру с активными заказами
                keyboard = []
                for active_order in active_orders:
                    status_emoji = {
                        'new': '📝',
                        'in_progress': '⚙️',
                        'ready': '✅'
                    }.get(active_order.status, '')
                    keyboard.append([f'{status_emoji} Заказ №{active_order.order_number}'])
                keyboard.extend([
                    ['📍 Узнать геопозицию'],
                    ['🔙 Вернуться назад']
                ])
                
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text(
                    f'Выберите заказ для просмотра информации:',
                    reply_markup=reply_markup
                )
                return PHONE
            else:
                keyboard = [
                    ['📍 Узнать геопозицию'],
                    ['🔙 Вернуться назад']
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text(
                    'Заказ не найден.',
                    reply_markup=reply_markup
                )
                return PHONE
        else:
            # Пробуем обработать как номер телефона
            return await self.process_phone(update, text)

    @sync_to_async
    def get_order_by_number(self, order_number):
        """Получение заказа по номеру"""
        try:
            return Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return None

    @sync_to_async
    def get_client_by_phone(self, phone):
        """Получение клиента по номеру телефона"""
        try:
            clean_phone = ''.join(filter(str.isdigit, phone))
            
            if len(clean_phone) == 11:
                print(f"Ищем клиента с номером: {clean_phone}")
                
                try:
                    return Client.objects.get(phone=clean_phone)
                except Client.DoesNotExist:
                    if clean_phone.startswith('7') or clean_phone.startswith('8'):
                        alt_phone = clean_phone[1:]
                        print(f"Пробуем альтернативный номер: {alt_phone}")
                        try:
                            return Client.objects.get(phone=alt_phone)
                        except Client.DoesNotExist:
                            pass
            
            print(f"Клиент не найден. Очищенный номер: {clean_phone}")
            return None
        except Exception as e:
            print(f"Ошибка при поиске клиента: {str(e)}")
            return None

    async def process_phone(self, update: Update, phone: str):
        """Обработка номера телефона"""
        # Форматируем номер телефона
        if phone.startswith('+'):
            phone = phone[1:]
        elif phone.startswith('8'):
            phone = '7' + phone[1:]
        elif phone.startswith('7'):
            phone = phone
        else:
            phone = '7' + phone

        # Ищем клиента по номеру телефона
        client = await self.get_client_by_phone(phone)
        
        if client:
            # Получаем активные заказы клиента
            orders = await self.get_active_orders(client)
            
            if orders:
                # Создаем клавиатуру с активными заказами
                keyboard = []
                for order in orders:
                    status_emoji = {
                        'new': '📝',
                        'in_progress': '⚙️',
                        'ready': '✅'
                    }.get(order.status, '')
                    keyboard.append([f'{status_emoji} Заказ №{order.order_number}'])
                keyboard.extend([
                    ['📍 Узнать геопозицию'],
                    ['🔙 Вернуться назад']
                ])
                
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text(
                    f'Найдены ваши заказы. Выберите заказ для просмотра информации:\n'
                    f'📝 - новые заказы\n'
                    f'⚙️ - заказы в работе\n'
                    f'✅ - готовые заказы',
                    reply_markup=reply_markup
                )
                return PHONE
            else:
                keyboard = [
                    ['📍 Узнать геопозицию'],
                    ['🔙 Вернуться назад']
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text(
                    f'У вас нет заказов.',
                    reply_markup=reply_markup
                )
                return PHONE
        else:
            keyboard = [
                ['📍 Узнать геопозицию'],
                ['🔙 Вернуться назад']
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                'Клиент с таким номером телефона не найден.',
                reply_markup=reply_markup
            )
            return PHONE

    @sync_to_async
    def get_active_orders(self, client):
        """Получение активных заказов клиента"""
        return list(Order.objects.filter(
            client=client,
            status__in=['new', 'in_progress', 'ready']
        ).order_by('-start_date'))

    @sync_to_async
    def get_client_total_debt(self, client):
        """Получение общей задолженности клиента"""
        total_debt = 0
        for order in Order.objects.filter(client=client):
            total_debt += order.get_debt()
        return total_debt

    @sync_to_async
    def get_order_client(self, order):
        """Получение клиента из заказа"""
        return order.client

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена разговора"""
        await update.message.reply_text(
            'До свидания! Для новой проверки используйте команду /start',
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    def run(self):
        """Запуск бота"""
        self.application.run_polling()

def create_order_form():
    form = {
        'customer_name': '',
        'phone': '',
        'order_description': '',
        'order_cost': '',
        'prepayment': '',
        'deadline': '',
        'status': 'new'
    }
    return form 