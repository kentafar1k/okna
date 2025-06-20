# Настройки для системы резервного копирования

# Настройки S3

# yandex s3
# S3_ENDPOINT_URL = 'https://storage.yandexcloud.net'  # Замените на URL своего S3-провайдера
# S3_REGION = 'ru-central1'  # Регион для S3 (зависит от провайдера)

S3_ACCESS_KEY = 'efd842cab8834dd6a26887990218e16d'  # Ключ доступа S3
S3_SECRET_KEY = '7c58fc66392c4b8c817b7ecec8886318'  # Секретный ключ S3
S3_BUCKET_NAME = 'backups-container'  # Имя бакета для хранения резервных копий
# S3_REGION = 'ru-central1'  # Регион для S3 (зависит от провайдера)

# Можно также настроить использование Selectel S3:
S3_ENDPOINT_URL = 'https://s3.ru-7.storage.selcloud.ru'
S3_REGION = 'ru-7'
# S3_ENDPOINT_URL = 'https://s3.storage.selcloud.ru'
# S3_REGION = 'ru-1'


# Настройки резервного копирования
# Максимальное количество резервных копий для хранения
MAX_BACKUPS = 14

# Настройки для бэкапа файлов медиа (если нужно)
BACKUP_MEDIA = True  # Установите True, чтобы включить медиа-файлы в бэкап

# Путь к директории с медиа-файлами (относительно корня проекта)
MEDIA_DIR = 'media'