# 🚀 Migration Guide - Enterprise Refactoring

**OneTop Backend - Hướng dẫn chuyển đổi sang Settings Module**

## ⚠️ Quan Trọng

**File `onetop_backend/settings.py` cũ vẫn còn** để tránh break existing code. Sau khi verify mọi thứ hoạt động, bạn có thể:
1. Backup file cũ: `mv settings.py settings.py.backup`
2. Hoặc xóa hẳn nếu không cần

---

## 📋 Checklist Migration

### 1. Kiểm tra Settings Package

```bash
# Verify structure
ls onetop_backend/settings/
# Expected output:
# __init__.py  base.py  dev.py  prod.py
```

### 2. Test Development Environment

```bash
# Không cần set biến môi trường
python manage.py check
python manage.py migrate
python manage.py runserver
```

**Expected:** Server chạy bình thường, không có lỗi import.

### 3. Test Settings Loading

```bash
python manage.py shell
```

```python
from django.conf import settings

# Check settings được load từ dev.py
print(settings.DEBUG)  # Should be True

# Check custom settings
print(settings.WEBSOCKET_TICKET_EXPIRY)  # Should be 10
print(settings.FRONTEND_URL)  # Should have value from .env
```

### 4. Verify Service Layer

```bash
python manage.py shell
```

```python
from apps.payments.services import PaymentService, VNPayService
from apps.users.models import User
from apps.payments.models import ServicePackage

# Test service import thành công
print(PaymentService)
print(VNPayService)

# Test create payment (cần có user và package trong DB)
# user = User.objects.first()
# result = PaymentService.create_payment_transaction(user, package_id=1)
# print(result.keys())  # Should have: payment_url, transaction_code, transaction
```

### 5. Verify i18n Setup

```bash
# Tạo translation files
python manage.py makemessages -l en

# Check file được tạo
ls locale/en/LC_MESSAGES/
# Expected: django.po
```

Mở file `locale/en/LC_MESSAGES/django.po` và dịch:

```po
msgid "You have already applied for this job."
msgstr "You have already applied for this job."

msgid "Your CV is ready for download"
msgstr "Your CV is ready for download"
```

Compile:
```bash
python manage.py compilemessages
```

Test:
```python
from django.utils.translation import activate, gettext as _

activate('en')
print(_("You have already applied for this job."))
# Output: "You have already applied for this job."

activate('vi')
print(_("You have already applied for this job."))
# Output: "Bạn đã ứng tuyển vào công việc này rồi." (if translated)
```

### 6. Test Celery Tasks

```bash
# Start Celery worker
celery -A onetop_backend worker --loglevel=info
```

Test notification task:
```python
from apps.notifications.tasks import send_websocket_notification

# Test task import
print(send_websocket_notification)

# Test delay (async)
send_websocket_notification.delay(
    recipient_id=1,
    notification_data={'id': '123', 'verb': 'test', 'description': 'Test', 'is_read': False}
)
# Check worker logs: Should see "Sent WebSocket notification to user 1"
```

---

## 🐳 Docker Migration

### Update docker-compose.yml

File đã được cập nhật với security improvements:
- Redis: Không expose port ra host
- Elasticsearch: Chỉ bind `127.0.0.1:9200` (localhost only)
- Database: Không expose port (internal only)

### Rebuild Containers

```bash
# Stop và xóa containers cũ
docker-compose down

# Rebuild images
docker-compose build --no-cache web celery_worker celery_beat

# Start lại
docker-compose up -d

# Check logs
docker-compose logs -f web
```

### Verify trong Container

```bash
# Exec vào container
docker-compose exec web python manage.py shell
```

```python
from django.conf import settings
print(settings.DEBUG)  # Should be True (hoặc False nếu set DJANGO_ENV=prod)
print(settings.DATABASES)
```

---

## 🚀 Production Deployment

### 1. Set Environment Variables

```bash
# .env hoặc server config
export DJANGO_ENV=prod
export FRONTEND_URL=https://onetop.vn
export CORS_ALLOWED_ORIGINS=https://onetop.vn,https://app.onetop.vn
export SECRET_KEY=your-secret-key-here
```

**Important:** `FRONTEND_URL` và `CORS_ALLOWED_ORIGINS` **bắt buộc** trong production. Nếu không set, app sẽ raise ValueError.

### 2. Create Logs Directory

```bash
mkdir -p logs
chmod 755 logs
```

### 3. Collectstatic

```bash
DJANGO_ENV=prod python manage.py collectstatic --noinput
```

### 4. Migrate Database

```bash
DJANGO_ENV=prod python manage.py migrate
```

### 5. Start Services

```bash
# Gunicorn (Web server)
DJANGO_ENV=prod gunicorn onetop_backend.wsgi:application \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log

# Daphne (WebSocket server)
DJANGO_ENV=prod daphne -b 0.0.0.0 -p 8001 onetop_backend.asgi:application

# Celery Worker
DJANGO_ENV=prod celery -A onetop_backend worker --loglevel=info

# Celery Beat
DJANGO_ENV=prod celery -A onetop_backend beat --loglevel=info
```

### 6. Verify Production Settings

```bash
DJANGO_ENV=prod python manage.py shell
```

```python
from django.conf import settings

# Check production settings
print(settings.DEBUG)  # Should be False
print(settings.SECURE_SSL_REDIRECT)  # Should be True
print(settings.SESSION_COOKIE_SECURE)  # Should be True
print(settings.FRONTEND_URL)  # Should be your production URL
```

---

## 🧪 Testing Regression

Run existing tests to ensure nothing breaks:

```bash
# Run all tests
pytest

# Run specific apps
pytest apps/payments/
pytest apps/notifications/

# With coverage
pytest --cov=apps --cov-report=html
```

**Expected:** Tất cả tests pass như trước, không có regression.

---

## 🔄 Rollback Plan (Nếu Cần)

Nếu gặp vấn đề, rollback ngay lập tức:

```bash
# 1. Rename settings package
mv onetop_backend/settings onetop_backend/settings_refactored

# 2. settings.py cũ sẽ được Django load lại
python manage.py runserver
# Should work như cũ

# 3. Restore code changes
git checkout apps/payments/views.py apps/notifications/signals.py
```

---

## 📞 Troubleshooting

### Issue 1: ImportError - No module named 'settings.base'

**Nguyên nhân:** File `__init__.py` thiếu hoặc bị lỗi syntax.

**Fix:**
```bash
ls onetop_backend/settings/__init__.py
# Nếu không tồn tại, tạo lại
```

### Issue 2: ValueError - FRONTEND_URL must be set

**Nguyên nhân:** Chạy production mode nhưng chưa set biến môi trường.

**Fix:**
```bash
export FRONTEND_URL=https://your-domain.com
# Hoặc thêm vào .env
```

### Issue 3: CORS errors in frontend

**Nguyên nhân:** `CORS_ALLOWED_ORIGINS` chưa cấu hình đúng.

**Fix:**
```bash
# Development
export CORS_ALLOW_ALL_ORIGINS=True

# Production
export CORS_ALLOWED_ORIGINS=https://onetop.vn,https://app.onetop.vn
```

### Issue 4: Celery tasks không chạy

**Nguyên nhân:** Worker chưa import được task mới.

**Fix:**
```bash
# Restart worker
pkill -f 'celery worker'
celery -A onetop_backend worker --loglevel=info
```

---

## ✅ Success Criteria

Migration hoàn thành khi:

- [ ] `python manage.py check` không có errors
- [ ] `pytest` pass tất cả tests
- [ ] Server chạy bình thường với `runserver`
- [ ] Docker containers start thành công
- [ ] Payment flow hoạt động (test tạo giao dịch)
- [ ] Notification WebSocket hoạt động
- [ ] i18n có thể switch language (nếu đã compile messages)
- [ ] Production mode load đúng settings (DEBUG=False, SSL=True)

---

## 📚 Next Steps

Sau khi migration thành công:

1. **Deploy lên Staging** để test trên môi trường giống Production
2. **Monitor logs** trong 24h đầu
3. **Backup database** trước khi deploy Production
4. **Gradual rollout:** Deploy 1 container trước, monitor, rồi scale
5. **Update documentation** cho team về cách sử dụng settings mới

---

**Good luck! 🚀**

Nếu cần hỗ trợ, check `ENTERPRISE_REFACTORING.md` để hiểu chi tiết các thay đổi.
