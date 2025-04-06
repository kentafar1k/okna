# Система резервного копирования для Django-проекта

Эта система предназначена для автоматического создания резервных копий базы данных и медиа-файлов вашего проекта Django с хранением их в S3-совместимом облачном хранилище.

## Возможности

- Автоматическое создание резервных копий базы данных (PostgreSQL, SQLite)
- Опциональное резервное копирование медиа-файлов
- Хранение только указанного количества последних резервных копий (по умолчанию 2)
- Автоматическое удаление старых копий
- Загрузка резервных копий в S3-совместимое облачное хранилище
- Запуск по расписанию через cron

## Установка и настройка

### 1. Установка зависимостей

Установите необходимые пакеты Python:

```bash
pip install boto3
```

### 2. Настройка параметров

Отредактируйте файл `backup_settings.py`, указав настройки вашего S3-хранилища и параметры резервного копирования:

```python
# Настройки S3
S3_ENDPOINT_URL = 'https://storage.yandexcloud.net'  # Замените на URL своего S3-провайдера
S3_ACCESS_KEY = 'your_access_key'  # Ключ доступа S3
S3_SECRET_KEY = 'your_secret_key'  # Секретный ключ S3
S3_BUCKET_NAME = 'your-backup-bucket'  # Имя бакета для хранения резервных копий
S3_REGION = 'ru-central1'  # Регион для S3 (зависит от провайдера)

# Максимальное количество резервных копий для хранения
MAX_BACKUPS = 2

# Включить резервное копирование медиа-файлов (True/False)
BACKUP_MEDIA = True

# Путь к директории с медиа-файлами (относительно корня проекта)
MEDIA_DIR = 'media'
```

#### Настройка для разных S3-провайдеров:

##### Yandex Cloud Object Storage
```python
S3_ENDPOINT_URL = 'https://storage.yandexcloud.net'
S3_REGION = 'ru-central1'
```

##### Selectel S3
```python
S3_ENDPOINT_URL = 'https://s3.storage.selcloud.ru'
S3_REGION = 'ru-1'
```

##### VK Cloud
```python
S3_ENDPOINT_URL = 'https://hb.bizmrg.com'
S3_REGION = 'ru-msk'
```

##### Mail.ru Cloud Solutions
```python
S3_ENDPOINT_URL = 'https://hb.bizmrg.com'
S3_REGION = 'ru-1'
```

### 3. Настройка cron-задания

Для автоматического запуска резервного копирования, сделайте скрипт `cron_setup.sh` исполняемым и запустите его:

```bash
chmod +x cron_setup.sh
./cron_setup.sh
```

Скрипт предложит выбрать время для ежедневного запуска резервного копирования.

### 4. Создание бакета S3

Перед использованием убедитесь, что у вас создан бакет в облачном хранилище S3 или скрипт автоматически создаст его при первом запуске (если у вашего аккаунта есть необходимые разрешения).

## Ручной запуск

Для ручного создания резервной копии выполните:

```bash
python backup_manager.py
```

## Лог резервного копирования

Информация о процессе резервного копирования записывается в файл `backup.log` в корне проекта.

## Восстановление из резервной копии

### Восстановление базы данных PostgreSQL

```bash
# Загрузите файл из S3 через веб-интерфейс или командой:
aws s3 cp s3://your-backup-bucket/db_backup_YYYYMMDD_HHMMSS.sql.gz . --endpoint-url=https://storage.yandexcloud.net

# Разархивируем файл
gunzip -c db_backup_YYYYMMDD_HHMMSS.sql.gz > backup_file.sql

# Восстанавливаем базу данных
psql -U username -d database_name -f backup_file.sql
```

### Восстановление базы данных SQLite

```bash
# Загрузите файл из S3
aws s3 cp s3://your-backup-bucket/db_backup_YYYYMMDD_HHMMSS.sql.gz . --endpoint-url=https://storage.yandexcloud.net

# Разархивируем файл
gunzip -c db_backup_YYYYMMDD_HHMMSS.sql.gz > database.sqlite3
```

### Восстановление медиа-файлов

```bash
# Загрузите файл из S3
aws s3 cp s3://your-backup-bucket/media_backup_YYYYMMDD_HHMMSS.tar.gz . --endpoint-url=https://storage.yandexcloud.net

# Разархивируем файл
tar -xzf media_backup_YYYYMMDD_HHMMSS.tar.gz -C /path/to/project/
```

## Устранение неполадок

### Ошибка авторизации в S3

- Проверьте правильность учетных данных в файле `backup_settings.py`
- Убедитесь, что у вашего аккаунта есть доступ к облачному хранилищу
- Проверьте, что S3_ENDPOINT_URL соответствует вашему провайдеру

### Cron не запускает задание

- Проверьте статус службы cron: `systemctl status cron`
- Проверьте права доступа: `chmod +x backup_manager.py`
- Проверьте логи cron: `grep CRON /var/log/syslog`

### Ошибка создания резервной копии БД

- Для PostgreSQL убедитесь, что утилита `pg_dump` установлена и доступна в PATH
- Для SQLite проверьте права доступа к файлу базы данных 