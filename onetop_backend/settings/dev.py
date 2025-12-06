"""
Development Settings
Cấu hình cho môi trường phát triển
"""

from .base import *

# --- DEBUG MODE ---
DEBUG = True

# --- SECURITY (Lỏng lẻo cho dev) ---
ALLOWED_HOSTS = ['*']

# CORS allow all cho dev
CORS_ALLOW_ALL_ORIGINS = True

# --- EMAIL (Console backend cho dev) ---
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# --- LOGGING (Chi tiết cho dev) ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',  # Bỏ comment để xem SQL queries: 'DEBUG'
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# --- CELERY (Eager mode cho dev - không cần Redis) ---
# CELERY_TASK_ALWAYS_EAGER = True  # Uncomment để chạy task đồng bộ (test)
# CELERY_TASK_EAGER_PROPAGATES = True

# --- ELASTICSEARCH (Có thể dùng local cho dev) ---
# ELASTICSEARCH_DSL = {
#     'default': {
#         'hosts': 'http://localhost:9200'
#     },
# }
