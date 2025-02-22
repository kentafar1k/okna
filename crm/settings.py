import os
import dj_database_url

# ... остальные настройки ...

# Database
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600
    )
}

# Добавьте домен Render в ALLOWED_HOSTS
ALLOWED_HOSTS = ['ваш.домен.ru', 'localhost']

# Настройка статических файлов
STATIC_ROOT = os.path.join(BASE_DIR, 'static') 