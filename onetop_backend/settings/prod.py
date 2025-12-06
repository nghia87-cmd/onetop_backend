"""
Production Settings
Cấu hình cho môi trường production - BẢO MẬT CAO
"""

from .base import *

# --- SENTRY INTEGRATION (Centralized Error Tracking) ---
try:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    print("⚠️ sentry-sdk not installed. Run: pip install sentry-sdk")

# --- DEBUG MODE ---
DEBUG = False

# --- SENTRY INITIALIZATION ---
if SENTRY_AVAILABLE and SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        environment=SENTRY_ENVIRONMENT,
        
        # Performance Monitoring (APM)
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions (recommended for production)
        profiles_sample_rate=1.0,
        
        # Send default PII (Personally Identifiable Information)
        send_default_pii=False,  # Bảo mật - không gửi thông tin cá nhân
        
        # Before sending events, this function will be called
        before_send=lambda event, hint: event if event.get('level') != 'debug' else None,
    )
    print(f"✅ Sentry initialized for environment: {SENTRY_ENVIRONMENT}")
elif not SENTRY_DSN:
    print("⚠️ SENTRY_DSN not set - running without centralized error tracking")
else:
    print("⚠️ Sentry SDK not available - install with: pip install sentry-sdk")

# --- SECURITY SETTINGS ---
# FRONTEND_URL bắt buộc phải có trong production
if not FRONTEND_URL:
    raise ValueError("FRONTEND_URL must be set in production environment")

# SSL/HTTPS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 năm
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# --- CORS (Strict cho production) ---
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
if not CORS_ALLOWED_ORIGINS:
    raise ValueError("CORS_ALLOWED_ORIGINS must be set in production")

# --- EMAIL (SMTP thật cho production) ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# --- LOGGING (Production-level with Structured JSON) ---
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """
    Custom formatter for structured JSON logging
    Compatible with ELK Stack, CloudWatch, Datadog, etc.
    """
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields (request_id, user_id, etc.)
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        
        return json.dumps(log_data, ensure_ascii=False)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': JSONFormatter,
        },
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'json',  # Use JSON formatter
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',  # Use JSON formatter for console too
        },
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apps': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Tạo thư mục logs nếu chưa có
import os
logs_dir = BASE_DIR / 'logs'
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# --- CACHING (Redis cho production) ---
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'onetop',
        'TIMEOUT': 300,  # 5 phút
    }
}

# --- DATABASE (Connection pooling cho production) ---
# DATABASES['default']['CONN_MAX_AGE'] = 600  # Uncomment nếu dùng persistent connections

# --- STATIC FILES (WhiteNoise compression) ---
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
