# 🚀 Quick Start: Deploy Backend lên Render

## ⚡ 5 Bước Deploy (30 phút)

### 1️⃣ Tạo Database (5 phút)
```
1. Vào https://dashboard.render.com
2. New → PostgreSQL
   Name: onetop-db
   Plan: Free
3. Copy "Internal Database URL"
```

### 2️⃣ Tạo Redis (2 phút)
```
1. New → Redis
   Name: onetop-redis
   Plan: Free
2. Copy "Internal Redis URL"
```

### 3️⃣ Deploy Backend (15 phút)
```
1. New → Web Service
2. Connect GitHub: nghia87-cmd/onetop_backend
3. Cấu hình:
   Name: onetop-backend
   Build Command: ./build.sh
   Start Command: daphne -b 0.0.0.0 -p $PORT onetop_backend.asgi:application
4. Environment Variables:
   SECRET_KEY = [generate random 64 chars]
   DEBUG = False
   ALLOWED_HOSTS = .onrender.com
   DATABASE_URL = [paste từ bước 1]
   REDIS_URL = [paste từ bước 2]
   CELERY_BROKER_URL = [paste từ bước 2]
   CELERY_RESULT_BACKEND = [paste từ bước 2]
   CORS_ALLOWED_ORIGINS = https://your-frontend.vercel.app
   CSRF_TRUSTED_ORIGINS = https://your-frontend.vercel.app
   FRONTEND_URL = https://your-frontend.vercel.app
5. Create Web Service
```

**Generate SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 4️⃣ Deploy Celery Worker (5 phút)
```
1. New → Background Worker
   Name: onetop-celery-worker
   Build: pip install -r requirements/base.txt
   Start: celery -A onetop_backend worker --loglevel=info
2. Copy tất cả env vars từ web service
```

### 5️⃣ Tạo Superuser (3 phút)
```
1. Vào onetop-backend service
2. Shell tab
3. python manage.py createsuperuser
```

---

## ✅ Kiểm Tra

```bash
# API
https://onetop-backend.onrender.com/api/v1/

# Swagger
https://onetop-backend.onrender.com/api/schema/swagger-ui/

# Admin
https://onetop-backend.onrender.com/admin/
```

---

## 📝 Lưu Ý

- ✅ Free tier: 750h/month (đủ chạy 24/7)
- ⚠️ Free tier sleep sau 15 phút không dùng (cold start ~30s)
- ⚠️ PostgreSQL free chỉ 90 ngày, sau đó $7/month
- 💡 Upgrade Starter ($7/mo) để không sleep

---

## 🆘 Lỗi Thường Gặp

**Build failed:**
```bash
# Kiểm tra build.sh có quyền execute:
chmod +x build.sh
git add build.sh
git commit -m "fix: chmod build.sh"
git push
```

**CORS error:**
```env
# Đảm bảo không có trailing slash:
CORS_ALLOWED_ORIGINS=https://your-app.vercel.app
# KHÔNG: https://your-app.vercel.app/
```

**WebSocket failed:**
```bash
# Kiểm tra Start Command:
daphne -b 0.0.0.0 -p $PORT onetop_backend.asgi:application
# KHÔNG dùng gunicorn cho WebSocket!
```

---

**Chi tiết đầy đủ:** Xem `RENDER_DEPLOY.md`
