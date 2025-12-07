# 🚀 Deploy Django Backend lên Render.com

## 📋 Tổng Quan

Render.com là platform deploy tương tự Railway, hỗ trợ:
- ✅ PostgreSQL managed database (Free tier: 90 days, sau đó $7/month)
- ✅ Redis managed (Free tier: 25MB)
- ✅ Auto-deploy từ GitHub
- ✅ SSL/HTTPS tự động
- ✅ Environment variables management
- ✅ Hỗ trợ WebSockets (Daphne/Channels)
- ✅ Celery workers

**Chi phí:**
- Free tier: 750 giờ/tháng (đủ chạy 24/7 cho 1 service)
- Starter: $7/month/service
- PostgreSQL: Free 90 ngày, sau đó $7/month

---

## 🎯 Bước 1: Chuẩn Bị Repository

### 1.1. Commit các file mới

```bash
cd onetop_backend

# Add files
git add build.sh render.yaml onetop_backend/settings.py
git commit -m "feat: Add Render deployment configuration"
git push origin main
```

### 1.2. Kiểm tra requirements

File `requirements/base.txt` đã sẵn sàng với:
- ✅ Django 5.x
- ✅ Daphne (ASGI server)
- ✅ Channels (WebSocket)
- ✅ Celery + Redis
- ✅ PostgreSQL (psycopg)
- ✅ gunicorn, whitenoise

---

## 🌐 Bước 2: Tạo Tài Khoản Render

1. Truy cập: https://render.com
2. Sign up với GitHub
3. Authorize Render truy cập repository `onetop`

---

## 🗄️ Bước 3: Tạo PostgreSQL Database

1. **Dashboard** → **New** → **PostgreSQL**

2. **Cấu hình:**
   ```
   Name: onetop-db
   Database: onetop
   User: onetop
   Region: Singapore (hoặc gần nhất)
   Plan: Free (90 days trial)
   ```

3. **Create Database**

4. **Lưu lại thông tin:**
   - Internal Database URL (dùng cho backend)
   - External Database URL (dùng cho local migration)

---

## 🔴 Bước 4: Tạo Redis Instance

1. **Dashboard** → **New** → **Redis**

2. **Cấu hình:**
   ```
   Name: onetop-redis
   Region: Singapore (cùng region với PostgreSQL)
   Plan: Free (25MB)
   Maxmemory Policy: allkeys-lru
   ```

3. **Create Redis**

4. **Lưu lại:**
   - Internal Redis URL

---

## 🚀 Bước 5: Deploy Backend (Web Service)

### 5.1. Tạo Web Service

1. **Dashboard** → **New** → **Web Service**

2. **Connect Repository:**
   - Chọn `onetop` repository
   - Root Directory: `onetop_backend` (nếu repo có cả frontend)
   - Branch: `main`

3. **Cấu hình Service:**
   ```
   Name: onetop-backend
   Runtime: Python 3
   Region: Singapore
   Branch: main
   Build Command: ./build.sh
   Start Command: daphne -b 0.0.0.0 -p $PORT onetop_backend.asgi:application
   Plan: Free (hoặc Starter $7/mo)
   ```

### 5.2. Cấu hình Environment Variables

Click **Advanced** → **Add Environment Variable**:

```env
# Django Core
SECRET_KEY=<generate-random-64-chars>
DEBUG=False
ALLOWED_HOSTS=.onrender.com
PYTHON_VERSION=3.11.9

# Database (Copy từ PostgreSQL service)
DATABASE_URL=postgresql://onetop:password@dpg-xxx.singapore-postgres.render.com/onetop

# Redis (Copy từ Redis service)
REDIS_URL=redis://red-xxx.singapore.redis.render.com:6379
CELERY_BROKER_URL=redis://red-xxx.singapore.redis.render.com:6379
CELERY_RESULT_BACKEND=redis://red-xxx.singapore.redis.render.com:6379

# CORS/CSRF (Cập nhật sau khi có frontend URL)
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
CSRF_TRUSTED_ORIGINS=https://your-frontend.vercel.app

# Frontend
FRONTEND_URL=https://your-frontend.vercel.app

# Optional: Elasticsearch (nếu dùng)
ELASTICSEARCH_HOST=http://localhost:9200
```

**Generate SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5.3. Deploy

1. Click **Create Web Service**
2. Render sẽ:
   - Clone repository
   - Chạy `build.sh`:
     - Install dependencies
     - Collect static files
     - Run migrations
   - Start Daphne server
3. Đợi ~5-10 phút

### 5.4. Kiểm tra

URL: `https://onetop-backend.onrender.com`

Test endpoints:
```bash
# Health check
curl https://onetop-backend.onrender.com/api/v1/

# API docs
https://onetop-backend.onrender.com/api/schema/swagger-ui/
```

---

## 🔄 Bước 6: Deploy Celery Worker

### 6.1. Tạo Background Worker

1. **Dashboard** → **New** → **Background Worker**

2. **Cấu hình:**
   ```
   Name: onetop-celery-worker
   Runtime: Python 3
   Repository: onetop
   Root Directory: onetop_backend
   Branch: main
   Build Command: pip install -r requirements/base.txt
   Start Command: celery -A onetop_backend worker --loglevel=info
   Plan: Free
   ```

3. **Environment Variables:** (Copy từ web service)
   ```env
   SECRET_KEY=<same-as-web-service>
   DATABASE_URL=<same-as-web-service>
   REDIS_URL=<same-as-web-service>
   CELERY_BROKER_URL=<same-as-web-service>
   CELERY_RESULT_BACKEND=<same-as-web-service>
   PYTHON_VERSION=3.11.9
   ```

4. **Create Background Worker**

### 6.2. Tạo Celery Beat (Scheduled Tasks)

1. **Dashboard** → **New** → **Background Worker**

2. **Cấu hình:**
   ```
   Name: onetop-celery-beat
   Runtime: Python 3
   Start Command: celery -A onetop_backend beat --loglevel=info
   (Các config còn lại giống Celery Worker)
   ```

---

## 🔧 Bước 7: Tạo Superuser

### 7.1. Truy cập Shell

1. Vào **onetop-backend** service
2. **Shell** tab (góc phải)

### 7.2. Chạy lệnh:

```bash
python manage.py createsuperuser
# Nhập: username, email, password
```

---

## 🌍 Bước 8: Custom Domain (Optional)

### 8.1. Thêm Domain

1. **onetop-backend** → **Settings** → **Custom Domain**
2. Add: `api.yourdomain.com`

### 8.2. Cấu hình DNS

Tại nhà cung cấp domain (GoDaddy, Namecheap, etc):
```
Type: CNAME
Name: api
Value: onetop-backend.onrender.com
```

### 8.3. Update Environment Variables

```env
ALLOWED_HOSTS=api.yourdomain.com,.onrender.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

**Lưu ý:** SSL certificate tự động được Render cấp sau vài phút.

---

## 🔍 Bước 9: Monitoring & Logs

### 9.1. Xem Logs

**Realtime logs:**
- Dashboard → Service → **Logs** tab
- Auto-refresh

**Filter logs:**
```bash
# Trong Logs tab, tìm kiếm:
"ERROR"
"WARNING"
"500"
```

### 9.2. Metrics

- **Metrics** tab: CPU, Memory, Request count
- **Events** tab: Deploy history, restarts

### 9.3. Alerts (Paid plans)

Settings → Notifications:
- Email khi service down
- Slack integration

---

## 🐛 Troubleshooting

### ❌ Build Failed

**Lỗi:** `pip install failed`

**Fix:**
```bash
# Kiểm tra requirements/base.txt có lỗi syntax
# Đảm bảo Python version đúng trong env vars:
PYTHON_VERSION=3.11.9
```

### ❌ Database Connection Error

**Lỗi:** `could not connect to server`

**Fix:**
```env
# Dùng Internal Database URL (không phải External)
DATABASE_URL=postgresql://onetop:xxx@dpg-xxx-a.singapore-postgres.render.com/onetop
                                              ^^^^ có chữ "-a" cho internal
```

### ❌ Static Files Not Found

**Lỗi:** `404 for /static/admin/css/...`

**Fix:**
```bash
# Đảm bảo build.sh chạy:
python manage.py collectstatic --no-input

# Kiểm tra settings.py:
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
```

### ❌ CORS Error từ Frontend

**Lỗi:** `blocked by CORS policy`

**Fix:**
```env
# Cập nhật chính xác domain frontend:
CORS_ALLOWED_ORIGINS=https://onetop-frontend.vercel.app
CSRF_TRUSTED_ORIGINS=https://onetop-frontend.vercel.app

# Không có trailing slash!
# Dùng https:// chứ không phải http://
```

### ❌ WebSocket Connection Failed

**Lỗi:** `WebSocket connection to 'wss://...' failed`

**Fix:**
```bash
# Đảm bảo Daphne đang chạy (không phải gunicorn):
# Start Command:
daphne -b 0.0.0.0 -p $PORT onetop_backend.asgi:application

# Kiểm tra ASGI routing trong asgi.py
```

### ❌ Celery Tasks Not Running

**Fix:**
1. Kiểm tra **onetop-celery-worker** service đang chạy
2. Xem logs của worker: `Dashboard → onetop-celery-worker → Logs`
3. Kiểm tra Redis connection:
   ```bash
   # Trong Shell tab của web service:
   python -c "import redis; r = redis.from_url('$REDIS_URL'); print(r.ping())"
   ```

---

## 📊 Performance Optimization

### 1. Database Connection Pooling

File `settings.py` đã có:
```python
DATABASES = {
    'default': {
        ...
        'CONN_MAX_AGE': 600,  # 10 minutes
    }
}
```

### 2. Redis Caching

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

### 3. Gunicorn Workers (Alternative to Daphne)

**Nếu không dùng WebSocket**, có thể thay Daphne bằng Gunicorn:
```bash
# Start Command:
gunicorn onetop_backend.wsgi:application --bind 0.0.0.0:$PORT --workers 2
```

---

## 🔄 CI/CD - Auto Deploy

### Mặc định:

- ✅ Git push to `main` → Tự động deploy
- ✅ Pull Request → Tạo preview environment (Paid plan)

### Tắt auto-deploy:

Settings → Auto-Deploy → **Disable**

### Manual deploy:

Dashboard → Service → **Manual Deploy** → Deploy latest commit

---

## 💰 Cost Estimate

### Free Tier (Testing):
```
Web Service (Free): 750 hours/month
PostgreSQL (Free): 90 days trial
Redis (Free): 25MB, 90 days trial
Celery Worker (Free): 750 hours/month
Celery Beat (Free): 750 hours/month
------------------------------------
Total: $0/month (first 90 days)
```

### Production (After trial):
```
Web Service (Starter): $7/month
PostgreSQL (Starter): $7/month
Redis (Starter): $7/month
Celery Worker (Starter): $7/month
Celery Beat (Starter): $7/month
------------------------------------
Total: $35/month
```

**Lưu ý:** Free services sleep sau 15 phút không dùng, Starter không sleep.

---

## 🎯 Checklist Hoàn Thành

- [ ] PostgreSQL database tạo xong
- [ ] Redis instance tạo xong
- [ ] Web service deploy thành công
- [ ] Celery worker chạy
- [ ] Celery beat chạy
- [ ] Migrations đã chạy (`python manage.py migrate`)
- [ ] Superuser đã tạo
- [ ] Static files accessible
- [ ] API endpoints hoạt động (`/api/v1/`)
- [ ] WebSocket connect được (`/ws/`)
- [ ] CORS configured cho frontend
- [ ] Environment variables đầy đủ
- [ ] Custom domain (optional)

---

## 📚 Resources

- **Render Docs:** https://render.com/docs
- **Django on Render:** https://render.com/docs/deploy-django
- **Troubleshooting:** https://render.com/docs/troubleshooting

---

## 🆘 Support

**Render Community:**
- Discord: https://discord.gg/render
- Forum: https://community.render.com

**Dashboard:**
- https://dashboard.render.com

---

## ✅ Next Steps

Sau khi deploy backend:
1. ✅ Test API với Postman/Swagger
2. ✅ Deploy frontend (Vercel)
3. ✅ Update CORS_ALLOWED_ORIGINS
4. ✅ Connect frontend → backend
5. ✅ Test end-to-end flow
6. ✅ Monitor logs for errors

**Thời gian deploy tổng:** ~30-45 phút (bao gồm tạo database, services, config)
