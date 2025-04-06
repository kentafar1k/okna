#!/bin/bash

# Скрипт для настройки ежедневного запуска резервного копирования

# Определяем текущий путь к проекту
PROJECT_DIR=$(pwd)
BACKUP_SCRIPT="${PROJECT_DIR}/backup_manager.py"
PYTHON_PATH=$(which python3)

# Проверяем наличие скрипта резервного копирования
if [ ! -f "$BACKUP_SCRIPT" ]; then
    echo "Ошибка: Скрипт резервного копирования не найден по пути: $BACKUP_SCRIPT"
    exit 1
fi

# Проверяем наличие Python
if [ -z "$PYTHON_PATH" ]; then
    echo "Ошибка: Python3 не найден. Пожалуйста, установите Python3."
    exit 1
fi

# Проверяем установку boto3
echo "Проверка наличия boto3..."
if ! $PYTHON_PATH -c "import boto3" &> /dev/null; then
    echo "boto3 не установлен. Устанавливаем..."
    if ! $PYTHON_PATH -m pip install boto3; then
        echo "Ошибка: Не удалось установить boto3. Установите его вручную: pip install boto3"
        exit 1
    fi
    echo "boto3 успешно установлен"
fi

# Время запуска задания по умолчанию
DEFAULT_HOUR=2
DEFAULT_MINUTE=0

# Запрос времени для запуска бэкапа
read -p "Введите час для запуска бэкапа (0-23) [$DEFAULT_HOUR]: " HOUR
HOUR=${HOUR:-$DEFAULT_HOUR}

read -p "Введите минуту для запуска бэкапа (0-59) [$DEFAULT_MINUTE]: " MINUTE
MINUTE=${MINUTE:-$DEFAULT_MINUTE}

# Проверка корректности введенных значений
if ! [[ "$HOUR" =~ ^[0-9]+$ ]] || [ "$HOUR" -lt 0 ] || [ "$HOUR" -gt 23 ]; then
    echo "Ошибка: Некорректное значение часа. Используется значение по умолчанию: $DEFAULT_HOUR"
    HOUR=$DEFAULT_HOUR
fi

if ! [[ "$MINUTE" =~ ^[0-9]+$ ]] || [ "$MINUTE" -lt 0 ] || [ "$MINUTE" -gt 59 ]; then
    echo "Ошибка: Некорректное значение минуты. Используется значение по умолчанию: $DEFAULT_MINUTE"
    MINUTE=$DEFAULT_MINUTE
fi

# Создаем временный файл для crontab
TEMP_CRON=$(mktemp)

# Экспортируем текущий crontab
crontab -l > "$TEMP_CRON" 2>/dev/null

# Проверяем, есть ли уже задание для резервного копирования
if grep -q "backup_manager.py" "$TEMP_CRON"; then
    echo "Задание для резервного копирования уже существует в crontab."
    read -p "Хотите обновить его? (y/n): " UPDATE
    
    if [[ "$UPDATE" =~ ^[Yy]$ ]]; then
        # Удаляем существующее задание
        sed -i '/backup_manager.py/d' "$TEMP_CRON"
    else
        echo "Операция отменена."
        rm "$TEMP_CRON"
        exit 0
    fi
fi

# Предупреждение о необходимости настройки S3
echo
echo "ВНИМАНИЕ: Убедитесь, что вы настроили параметры S3 в файле backup_settings.py:"
echo "- S3_ENDPOINT_URL - URL вашего S3-провайдера"
echo "- S3_ACCESS_KEY - Ключ доступа"
echo "- S3_SECRET_KEY - Секретный ключ"
echo "- S3_BUCKET_NAME - Имя бакета для резервных копий"
echo "- S3_REGION - Регион хранилища"
echo
read -p "Продолжить настройку cron? (y/n): " CONTINUE
if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
    echo "Операция отменена."
    rm "$TEMP_CRON"
    exit 0
fi

# Добавляем новое задание
echo "# Ежедневное резервное копирование (настроено $(date '+%Y-%m-%d %H:%M:%S'))" >> "$TEMP_CRON"
echo "$MINUTE $HOUR * * * cd $PROJECT_DIR && $PYTHON_PATH $BACKUP_SCRIPT >> $PROJECT_DIR/backup.log 2>&1" >> "$TEMP_CRON"

# Применяем новый crontab
crontab "$TEMP_CRON"
rm "$TEMP_CRON"

echo "Задание cron настроено для запуска резервного копирования ежедневно в $HOUR:$MINUTE."
echo "Логи будут сохраняться в файл: $PROJECT_DIR/backup.log"

# Проверка статуса cron
if systemctl is-active --quiet cron; then
    echo "Служба cron активна и работает."
else
    echo "Предупреждение: Служба cron не запущена. Запустите её командой: sudo systemctl start cron"
fi

echo "Настройка завершена!"