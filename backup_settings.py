# Настройки для системы резервного копирования

# Настройки Selectel
SELECTEL_CONTAINER = 'your_container_name'  # Имя контейнера на Selectel
SELECTEL_USERNAME = 'your_username'  # Имя пользователя Selectel
SELECTEL_PASSWORD = 'your_password'  # Пароль Selectel
SELECTEL_AUTH_URL = 'https://api.selcdn.ru/auth/v1.0'

# Настройки резервного копирования
# Максимальное количество резервных копий для хранения
MAX_BACKUPS = 2  

# Настройки для бэкапа файлов медиа (если нужно)
BACKUP_MEDIA = False  # Установите True, если нужно включить медиа-файлы в бэкап

# Путь к директории с медиа-файлами (относительно корня проекта)
MEDIA_DIR = 'media' 