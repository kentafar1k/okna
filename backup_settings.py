# Настройки для системы резервного копирования

# Настройки Selectel
SELECTEL_CONTAINER = 'backups-container'  # Имя контейнера на Selectel
SELECTEL_USERNAME = 'andreibogd@mail.ru'  # Имя пользователя Selectel
SELECTEL_PASSWORD = 'Bogdan682356'  # Пароль Selectel
SELECTEL_AUTH_URL = 'https://api.selcdn.ru/auth/v1.0'

# Настройки резервного копирования
# Максимальное количество резервных копий для хранения
MAX_BACKUPS = 3

# Настройки для бэкапа файлов медиа (если нужно)
BACKUP_MEDIA = True  # Установите True, если нужно включить медиа-файлы в бэкап

# Путь к директории с медиа-файлами (относительно корня проекта)
MEDIA_DIR = 'media' 