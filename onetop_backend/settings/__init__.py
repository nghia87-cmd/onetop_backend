"""
Settings Package Initialization
Tự động load settings dựa trên DJANGO_SETTINGS_MODULE hoặc biến môi trường
"""

import os

# Đọc biến môi trường DJANGO_ENV (dev, prod, test)
# Mặc định là dev nếu không set
DJANGO_ENV = os.getenv('DJANGO_ENV', 'dev')

if DJANGO_ENV == 'prod':
    from .prod import *
elif DJANGO_ENV == 'test':
    from .dev import *  # Test dùng dev settings (có thể tạo test.py riêng)
else:
    from .dev import *
