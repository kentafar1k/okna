from django.core.management.base import BaseCommand
from bot.telegram_bot import OrderBot

# python manage.py runbot - в консоли чтобы запустить бота

class Command(BaseCommand):
    help = 'Запуск телеграм бота'

    def handle(self, *args, **options):
        self.stdout.write('Запуск бота...')
        bot = OrderBot()
        bot.run()

