"""
Django settings for backend project.
Full configured for: REST Framework, Channels (Realtime), Celery, JWT, Swagger.
"""

from pathlib import Path
import os
import environ
from datetime import timedelta
from celery.schedules import crontab

# --- 1. SETUP MÔI TRƯỜNG & ĐƯỜNG DẪN ---
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Khởi tạo Environ
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1'])
)

# Đọc file .env
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env('ALLOWED_HOSTS')


# --- 2. ỨNG DỤNG (APPS) ---
INSTALLED_APPS = [
    # A. Server & Realtime (Ưu tiên chạy trước)
    'daphne',          # Thay thế WSGI bằng ASGI server
    'channels',        # Hỗ trợ WebSockets

    # B. Django Apps mặc định
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_elasticsearch_dsl',  # Elasticsearch DSL integration
    'django.contrib.postgres',  # Sử dụng các trường Postgres nâng cao

    # C. Third-party Libraries
    'rest_framework',              # API
    'rest_framework_simplejwt',    # Authentication
    'drf_spectacular',             # Swagger Docs
    'corsheaders',                 # Kết nối Frontend (React/Remix/Vue)
    'django_filters',              # Filter dữ liệu
    'django_cleanup.apps.CleanupConfig', # Tự động xóa file ảnh khi xóa model

    # D. Local Apps (Đặt trong thư mục apps/)
    # Lưu ý: Trong file apps/<tên>/apps.py, name phải là 'apps.<tên>'
    'apps.core',           
    'apps.users',
    'apps.companies',
    'apps.jobs',
    'apps.resumes',
    'apps.applications',
    'apps.notifications',
    'apps.chats',
    'apps.payments',
]

# --- 3. MIDDLEWARE ---
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', # <--- Quan trọng: Phải đứng đầu để handle request từ Frontend
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # <--- Xử lý file tĩnh production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'onetop_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# --- 4. CẤU HÌNH SERVER & DATABASE ---
WSGI_APPLICATION = 'onetop_backend.wsgi.application'
ASGI_APPLICATION = 'onetop_backend.asgi.application' 

# Database
DATABASES = {
    'default': env.db('DATABASE_URL')
}

# --- 5. AUTHENTICATION (USER MODEL) ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Trỏ chính xác vào app users nằm trong thư mục apps
AUTH_USER_MODEL = 'users.User' 

# --- 6. LOCALIZATION ---
LANGUAGE_CODE = 'vi'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True


# --- 7. STATIC & MEDIA (DJANGO 4.2+ STYLE) ---
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Cấu hình Storages mới (Thay thế STATICFILES_STORAGE cũ)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


# --- 8. REST FRAMEWORK ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20, # Mặc định phân trang
}

# --- 9. JWT CONFIG ---
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# --- 10. SWAGGER (SPECTACULAR) ---
SPECTACULAR_SETTINGS = {
    'TITLE': 'OneTop Recruitment API',
    'DESCRIPTION': 'API documentation for OneTop recruitment platform',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True, # Tách request/response rõ ràng
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True, # Giữ trạng thái login khi reload
        'displayOperationId': True,
    },
}

# --- 11. CORS (FRONTEND CONNECTION) ---
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    "http://localhost:3000", 
    "http://localhost:5173", 
    "http://127.0.0.1:3000"
])
CORS_ALLOW_CREDENTIALS = True

# --- 12. EMAIL ---
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='OneTop Recruitment <noreply@onetop.com>')

# --- 13. REALTIME & ASYNC (REDIS) ---
# Chung 1 biến REDIS_URL cho cả Celery và Channels để dễ quản lý
REDIS_URL = env('REDIS_URL', default='redis://127.0.0.1:6379/0')

# Channels Configuration
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

# Celery Configuration
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Default Primary Key
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- 14. OTHER SETTINGS CAN BE ADDED BELOW ---

# --- CELERY BEAT SCHEDULE (LẬP LỊCH TASK TỰ ĐỘNG) ---

CELERY_BEAT_SCHEDULE = {
    'check-expired-memberships-every-day': {
        'task': 'apps.users.tasks.check_expired_memberships',
        'schedule': crontab(hour=0, minute=0),
    },
    # --- THÊM TASK MỚI ---
    'send-daily-job-alerts': {
        'task': 'apps.jobs.tasks.send_daily_job_alerts',
        'schedule': crontab(hour=8, minute=0), # 8 giờ sáng hàng ngày
        # 'schedule': 60.0, # (Bật dòng này nếu muốn test ngay mỗi phút)
    },

    'check-upcoming-interviews-every-5-minutes': {
        'task': 'apps.applications.tasks.check_upcoming_interviews',
        'schedule': crontab(minute='*/5'),
    },
}
# --- ELASTICSEARCH CONFIGURATION ---
ELASTICSEARCH_DSL = {
    'default': {
        'hosts': 'http://elasticsearch:9200'
    },
}