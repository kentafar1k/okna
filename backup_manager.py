import os
import sys
import datetime
import subprocess
import logging
import requests
from pathlib import Path
import django
from django.conf import settings
import shutil
import tarfile

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("backup.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('backup_manager')

# Добавляем путь проекта в PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Инициализируем Django для доступа к настройкам
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'okna.settings')
django.setup()

# Импортируем настройки бэкапов
try:
    from backup_settings import (
        SELECTEL_CONTAINER, SELECTEL_USERNAME, SELECTEL_PASSWORD,
        SELECTEL_AUTH_URL, MAX_BACKUPS, BACKUP_MEDIA, MEDIA_DIR
    )
except ImportError:
    logger.error("Файл backup_settings.py не найден! Используются значения по умолчанию.")
    # Настройки по умолчанию
    SELECTEL_CONTAINER = 'backups'
    SELECTEL_USERNAME = ''
    SELECTEL_PASSWORD = ''
    SELECTEL_AUTH_URL = 'https://api.selcdn.ru/auth/v1.0'
    MAX_BACKUPS = 2
    BACKUP_MEDIA = False
    MEDIA_DIR = 'media'

# Создаем директорию для бэкапов
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

# Глобальные переменные для Selectel
SELECTEL_STORAGE_URL = None
SELECTEL_AUTH_TOKEN = None

def authenticate_selectel():
    """Аутентификация в Selectel и получение токена"""
    global SELECTEL_STORAGE_URL, SELECTEL_AUTH_TOKEN

    if not SELECTEL_USERNAME or not SELECTEL_PASSWORD:
        logger.error("Не указаны учетные данные Selectel. Проверьте файл backup_settings.py")
        return False

    headers = {
        'X-Auth-User': SELECTEL_USERNAME,
        'X-Auth-Key': SELECTEL_PASSWORD
    }

    try:
        response = requests.get(SELECTEL_AUTH_URL, headers=headers)
        response.raise_for_status()

        SELECTEL_STORAGE_URL = response.headers.get('X-Storage-Url')
        SELECTEL_AUTH_TOKEN = response.headers.get('X-Auth-Token')

        logger.info('Успешная аутентификация в Selectel')
        return True
    except Exception as e:
        logger.error(f'Ошибка аутентификации в Selectel: {str(e)}')
        return False

def create_db_backup():
    """Создание резервной копии базы данных"""
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'db_backup_{timestamp}.sql'
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    db_settings = settings.DATABASES['default']

    try:
        if db_settings['ENGINE'] == 'django.db.backends.postgresql':
            # Создаем резервную копию PostgreSQL
            cmd = [
                'pg_dump',  #  r'C:\Program Files\PostgreSQL\16\bin\pg_dump.exe'
                '-h', db_settings['HOST'],
                '-p', str(db_settings.get('PORT', 5432)),
                '-U', db_settings['USER'],
                '-d', db_settings['NAME'],
                '-f', backup_path
            ]

            # Задаем переменную окружения для пароля
            env = os.environ.copy()
            env['PGPASSWORD'] = db_settings['PASSWORD']

            subprocess.run(cmd, env=env, check=True)

            # Сжимаем файл
            compressed_path = f"{backup_path}.gz"
            subprocess.run(['gzip', '-f', backup_path], check=True)

            logger.info(f'Резервная копия базы данных создана: {compressed_path}')
            return compressed_path

        elif db_settings['ENGINE'] == 'django.db.backends.sqlite3':
            # Создаем резервную копию SQLite
            db_path = db_settings['NAME']
            compressed_path = f"{backup_path}.gz"

            # Копируем файл БД
            shutil.copy2(db_path, backup_path)

            # Сжимаем файл
            subprocess.run(['gzip', '-f', backup_path], check=True)

            logger.info(f'Резервная копия базы данных создана: {compressed_path}')
            return compressed_path

        else:
            logger.error(f'Неподдерживаемый тип базы данных: {db_settings["ENGINE"]}')
            return None

    except Exception as e:
        logger.error(f'Ошибка создания резервной копии БД: {str(e)}')
        return None

def create_media_backup():
    """Создание резервной копии медиа-файлов"""
    if not BACKUP_MEDIA:
        logger.info('Резервное копирование медиа-файлов отключено')
        return None

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'media_backup_{timestamp}.tar.gz'
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    try:
        media_dir = os.path.join(BASE_DIR, MEDIA_DIR)

        if not os.path.exists(media_dir):
            logger.warning(f'Директория медиа-файлов не найдена: {media_dir}')
            return None

        # Создаем сжатый tar-архив
        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add(media_dir, arcname=os.path.basename(media_dir))

        logger.info(f'Резервная копия медиа-файлов создана: {backup_path}')
        return backup_path

    except Exception as e:
        logger.error(f'Ошибка создания резервной копии медиа-файлов: {str(e)}')
        return None

def upload_to_selectel(backup_file):
    """Загрузка резервной копии на Selectel"""
    if not SELECTEL_AUTH_TOKEN or not SELECTEL_STORAGE_URL:
        if not authenticate_selectel():
            return False

    try:
        filename = os.path.basename(backup_file)
        url = f"{SELECTEL_STORAGE_URL}/{SELECTEL_CONTAINER}/{filename}"

        headers = {'X-Auth-Token': SELECTEL_AUTH_TOKEN}

        with open(backup_file, 'rb') as f:
            response = requests.put(url, headers=headers, data=f)
            response.raise_for_status()

        logger.info(f'Файл {filename} успешно загружен на Selectel')
        return True
    except Exception as e:
        logger.error(f'Ошибка загрузки файла на Selectel: {str(e)}')
        return False

def list_selectel_backups(prefix='db_backup_'):
    """Получение списка бекапов на Selectel"""
    if not SELECTEL_AUTH_TOKEN or not SELECTEL_STORAGE_URL:
        if not authenticate_selectel():
            return []

    try:
        url = f"{SELECTEL_STORAGE_URL}/{SELECTEL_CONTAINER}?format=json"
        headers = {'X-Auth-Token': SELECTEL_AUTH_TOKEN}

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        backups = [item for item in response.json() if item['name'].startswith(prefix)]
        # Сортировка по дате создания (от старых к новым)
        backups.sort(key=lambda x: x['name'])

        logger.info(f'Получен список резервных копий на Selectel ({prefix}): {len(backups)} файлов')
        return backups
    except Exception as e:
        logger.error(f'Ошибка получения списка резервных копий: {str(e)}')
        return []

def delete_selectel_backup(filename):
    """Удаление бекапа с Selectel"""
    if not SELECTEL_AUTH_TOKEN or not SELECTEL_STORAGE_URL:
        if not authenticate_selectel():
            return False

    try:
        url = f"{SELECTEL_STORAGE_URL}/{SELECTEL_CONTAINER}/{filename}"
        headers = {'X-Auth-Token': SELECTEL_AUTH_TOKEN}

        response = requests.delete(url, headers=headers)
        response.raise_for_status()

        logger.info(f'Файл {filename} успешно удален с Selectel')
        return True
    except Exception as e:
        logger.error(f'Ошибка удаления файла с Selectel: {str(e)}')
        return False

def manage_backups(prefix='db_backup_'):
    """Управление резервными копиями: сохраняем только MAX_BACKUPS последних"""
    backups = list_selectel_backups(prefix)

    # Если у нас больше резервных копий, чем нужно, удаляем самые старые
    if len(backups) >= MAX_BACKUPS:
        # Сколько копий нужно удалить
        to_delete = len(backups) - MAX_BACKUPS + 1  # +1 для новой копии

        for i in range(to_delete):
            oldest_backup = backups[i]
            logger.info(f'Удаление старого бекапа: {oldest_backup["name"]}')
            delete_selectel_backup(oldest_backup['name'])

def cleanup_local_backups():
    """Удаление локальных резервных копий"""
    try:
        for file in os.listdir(BACKUP_DIR):
            if file.startswith(('db_backup_', 'media_backup_')):
                os.remove(os.path.join(BACKUP_DIR, file))
        logger.info('Локальные резервные копии удалены')
    except Exception as e:
        logger.error(f'Ошибка удаления локальных резервных копий: {str(e)}')

def main():
    """Основная функция создания и управления резервными копиями"""
    logger.info('Запуск процесса резервного копирования')

    # Создаем резервную копию базы данных
    db_backup_file = create_db_backup()
    if db_backup_file:
        # Загружаем на Selectel
        if upload_to_selectel(db_backup_file):
            # Управляем резервными копиями БД
            manage_backups('db_backup_')
        else:
            logger.error('Не удалось загрузить резервную копию БД на Selectel')

    # Создаем резервную копию медиа-файлов (если включено)
    if BACKUP_MEDIA:
        media_backup_file = create_media_backup()
        if media_backup_file:
            # Загружаем на Selectel
            if upload_to_selectel(media_backup_file):
                # Управляем резервными копиями медиа
                manage_backups('media_backup_')
            else:
                logger.error('Не удалось загрузить резервную копию медиа на Selectel')

    # Удаляем локальные копии
    cleanup_local_backups()

    logger.info('Процесс резервного копирования завершен')

if __name__ == '__main__':
    main()