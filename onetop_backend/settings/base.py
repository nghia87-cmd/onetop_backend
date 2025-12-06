"""
Base Django Settings
Cấu hình chung cho tất cả môi trường (dev, prod, test)
"""

from pathlib import Path
import os
import environ
from datetime import timedelta
from celery.schedules import crontab

# --- 1. SETUP MÔI TRƯỜNG & ĐƯỜNG DẪN ---
# Build paths: BASE_DIR là onetop_backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Khởi tạo Environ
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1'])
)

# Đọc file .env
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# DEBUG mặc định = False (sẽ override trong dev.py)
DEBUG = False

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

AUTH_USER_MODEL = 'users.User' 

# --- 6. LOCALIZATION ---
LANGUAGE_CODE = 'vi'  # Ngôn ngữ mặc định
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True  # Bật i18n
USE_TZ = True

# Ngôn ngữ hỗ trợ
LANGUAGES = [
    ('vi', 'Tiếng Việt'),
    ('en', 'English'),
]

# Đường dẫn chứa file translation (.po, .mo)
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# --- 7. STATIC & MEDIA FILES ---
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- 8. REST FRAMEWORK ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

# --- 9. JWT (SIMPLE JWT) ---
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
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    },
}

# --- 11. CORS ---
CORS_ALLOW_ALL_ORIGINS = env.bool('CORS_ALLOW_ALL_ORIGINS', default=True)

CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
])

# --- 12. EMAIL ---
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@onetop.vn')

# --- 13. VNPAY CONFIGURATION ---
VNPAY_TMN_CODE = env('VNPAY_TMN_CODE', default='')
VNPAY_HASH_SECRET = env('VNPAY_HASH_SECRET', default='')
VNPAY_URL = env('VNPAY_URL', default='https://sandbox.vnpayment.vn/paymentv2/vpcpay.html')
VNPAY_RETURN_URL = env('VNPAY_RETURN_URL', default='http://localhost:8000/api/v1/payments/vnpay/return/')

# --- 14. REDIS, CELERY, CHANNELS ---
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

# --- 15. CELERY BEAT SCHEDULE ---
CELERY_BEAT_SCHEDULE = {
    'check-expired-memberships-every-day': {
        'task': 'apps.users.tasks.check_expired_memberships',
        'schedule': crontab(hour=0, minute=0),
    },
    'send-daily-job-alerts': {
        'task': 'apps.jobs.tasks.send_daily_job_alerts',
        'schedule': crontab(hour=8, minute=0),
    },
    'check-upcoming-interviews-every-5-minutes': {
        'task': 'apps.applications.tasks.check_upcoming_interviews',
        'schedule': crontab(minute='*/5'),
    },
}

# --- 16. ELASTICSEARCH CONFIGURATION ---
ELASTICSEARCH_DSL = {
    'default': {
        'hosts': 'http://elasticsearch:9200'
    },
}

# --- 17. WEBSOCKET TICKET CONFIGURATION ---
WEBSOCKET_TICKET_EXPIRY = env.int('WEBSOCKET_TICKET_EXPIRY', default=10)

# --- 18. FRONTEND URL (REQUIRED IN PRODUCTION) ---
FRONTEND_URL = env('FRONTEND_URL', default='http://localhost:3000')
