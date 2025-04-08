import os
import sys
import datetime
import subprocess
import logging
from logging.handlers import RotatingFileHandler
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
import django
from django.conf import settings
import shutil
import tarfile

# Настройка логирования с ротацией файлов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            "backup.log", 
            maxBytes=1000000,  # Максимальный размер файла - 1MB
            backupCount=14      # Хранить до 14 файлов ротации
        )
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
        S3_ENDPOINT_URL, S3_ACCESS_KEY, S3_SECRET_KEY, 
        S3_BUCKET_NAME, S3_REGION, MAX_BACKUPS, BACKUP_MEDIA, MEDIA_DIR
    )
except ImportError:
    logger.error("Файл backup_settings.py не найден! Используются значения по умолчанию.")
    # Настройки по умолчанию
    S3_ENDPOINT_URL = 'https://s3.ru-7.storage.selcloud.ru'
    S3_ACCESS_KEY = ''
    S3_SECRET_KEY = ''
    S3_BUCKET_NAME = 'backups'
    S3_REGION = 'ru-7'
    MAX_BACKUPS = 14
    BACKUP_MEDIA = False
    MEDIA_DIR = 'media'

# Создаем директорию для бэкапов
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

def get_s3_client():
    """Создание клиента S3"""
    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            region_name=S3_REGION
        )
        # Проверяем соединение
        s3_client.list_buckets()
        return s3_client
    except Exception as e:
        logger.error(f"Ошибка подключения к S3: {str(e)}")
        return None

def ensure_bucket_exists(s3_client):
    """Убедиться, что бакет существует, создать если нет"""
    try:
        s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
        logger.info(f"Бакет {S3_BUCKET_NAME} существует")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            # Бакет не существует, создаем его
            try:
                if S3_REGION == 'us-east-1':
                    s3_client.create_bucket(Bucket=S3_BUCKET_NAME)
                else:
                    s3_client.create_bucket(
                        Bucket=S3_BUCKET_NAME,
                        CreateBucketConfiguration={'LocationConstraint': S3_REGION}
                    )
                logger.info(f"Создан новый бакет {S3_BUCKET_NAME}")
                return True
            except Exception as create_error:
                logger.error(f"Ошибка создания бакета: {str(create_error)}")
                return False
        else:
            logger.error(f"Ошибка доступа к бакету: {str(e)}")
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
                'pg_dump', # 'C:\\Program Files\\PostgreSQL\\16\\bin\\pg_dump.exe'
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

def upload_to_s3(s3_client, backup_file):
    """Загрузка резервной копии в S3"""
    if not s3_client:
        return False
    
    try:
        filename = os.path.basename(backup_file)
        
        # Загружаем файл в S3
        s3_client.upload_file(
            Filename=backup_file,
            Bucket=S3_BUCKET_NAME,
            Key=filename
        )
        
        logger.info(f'Файл {filename} успешно загружен в S3')
        return True
    except Exception as e:
        logger.error(f'Ошибка загрузки файла в S3: {str(e)}')
        return False

def list_s3_backups(s3_client, prefix='db_backup_'):
    """Получение списка бекапов в S3"""
    if not s3_client:
        return []
    
    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET_NAME,
            Prefix=prefix
        )
        
        backups = []
        if 'Contents' in response:
            for item in response['Contents']:
                backups.append({
                    'name': item['Key'],
                    'last_modified': item['LastModified'],
                    'size': item['Size']
                })
        
        # Сортировка по дате модификации (от старых к новым)
        backups.sort(key=lambda x: x['last_modified'])
        
        logger.info(f'Получен список резервных копий в S3 ({prefix}): {len(backups)} файлов')
        return backups
    except Exception as e:
        logger.error(f'Ошибка получения списка резервных копий: {str(e)}')
        return []

def delete_s3_backup(s3_client, filename):
    """Удаление бекапа из S3"""
    if not s3_client:
        return False
    
    try:
        s3_client.delete_object(
            Bucket=S3_BUCKET_NAME,
            Key=filename
        )
        
        logger.info(f'Файл {filename} успешно удален из S3')
        return True
    except Exception as e:
        logger.error(f'Ошибка удаления файла из S3: {str(e)}')
        return False

def manage_backups(s3_client, prefix='db_backup_'):
    """Управление резервными копиями: сохраняем только MAX_BACKUPS последних"""
    backups = list_s3_backups(s3_client, prefix)
    
    # Всегда оставляем только MAX_BACKUPS последних копий
    if len(backups) > MAX_BACKUPS:
        # Сколько копий нужно удалить
        to_delete = len(backups) - MAX_BACKUPS
        
        for i in range(to_delete):
            oldest_backup = backups[i]
            logger.info(f'Удаление старого бекапа: {oldest_backup["name"]}')
            delete_s3_backup(s3_client, oldest_backup['name'])

def cleanup_local_backups():
    """Удаление локальных резервных копий"""
    try:
        for file in os.listdir(BACKUP_DIR):
            if file.startswith(('db_backup_', 'media_backup_')):
                os.remove(os.path.join(BACKUP_DIR, file))
        logger.info('Локальные резервные копии удалены')
    except Exception as e:
        logger.error(f'Ошибка удаления локальных резервных копий: {str(e)}')

def cleanup_old_backups(s3_client):
    """Очистка старых бэкапов перед созданием новых"""
    # Очищаем старые бэкапы БД
    manage_backups(s3_client, 'db_backup_')
    # Очищаем старые бэкапы медиа
    if BACKUP_MEDIA:
        manage_backups(s3_client, 'media_backup_')

def main():
    """Основная функция создания и управления резервными копиями"""
    logger.info('Запуск процесса резервного копирования')
    
    # Инициализируем S3 клиент
    s3_client = get_s3_client()
    if not s3_client:
        logger.error('Не удалось инициализировать S3 клиент')
        return
    
    # Проверяем существование бакета
    if not ensure_bucket_exists(s3_client):
        logger.error(f'Бакет {S3_BUCKET_NAME} недоступен')
        return
    
    # Создаем резервную копию базы данных
    db_backup_file = create_db_backup()
    if db_backup_file:
        # Загружаем в S3
        if not upload_to_s3(s3_client, db_backup_file):
            logger.error('Не удалось загрузить резервную копию БД в S3')
    
    # Создаем резервную копию медиа-файлов (если включено)
    if BACKUP_MEDIA:
        media_backup_file = create_media_backup()
        if media_backup_file:
            # Загружаем в S3
            if not upload_to_s3(s3_client, media_backup_file):
                logger.error('Не удалось загрузить резервную копию медиа в S3')
    
    # Очищаем старые бэкапы после создания новых
    cleanup_old_backups(s3_client)
    
    # Удаляем локальные копии
    cleanup_local_backups()
    
    logger.info('Процесс резервного копирования завершен')

if __name__ == '__main__':
    main()