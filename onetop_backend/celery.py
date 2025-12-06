# backend/celery.py
import os
from celery import Celery

# Thiết lập biến môi trường mặc định là file settings của Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onetop_backend.settings')

# Tạo instance Celery (tên là 'backend')
app = Celery('onetop_backend')

# Đọc cấu hình từ Django settings, các biến Celery phải bắt đầu bằng 'CELERY_'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Tự động tìm tasks trong các app con (apps/...)
app.autodiscover_tasks()