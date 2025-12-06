# OneTop Backend

## Giới thiệu

Đây là backend Django cho dự án OneTop. Bao gồm nhiều ứng dụng con (users, companies, jobs, chats, notifications, payments, resumes, applications, ...). Hướng dẫn dưới đây mô tả cách cấu hình môi trường, chạy server, celery, docker và test.

## Công nghệ chính

- Python 3.8+ (tuỳ dự án)
- Django
- Celery (công việc bất đồng bộ)
- Redis / RabbitMQ (tuỳ cấu hình cho Celery)
- Docker & docker-compose (tùy chọn)

## Yêu cầu

- Git
- Python 3.8+
- Virtualenv/venv
- Docker & Docker Compose (nếu muốn chạy container)

## Cài đặt nhanh (Local, PowerShell trên Windows)

1. Tạo virtualenv và kích hoạt:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Cài đặt dependencies:

```powershell
pip install -r requirements.txt
```

3. Sao chép file môi trường và chỉnh sửa nếu cần:

```powershell
copy .env.example .env
# Sau đó chỉnh .env theo cấu hình (DB, Redis, email...)
```

4. Chạy migrations và tạo superuser:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

5. Chạy server Django:

```powershell
python manage.py runserver 0.0.0.0:8000
```

## Biến môi trường (ví dụ)

File `.env.example` có sẵn trong repo. Một số biến thường cần thiết:

- `DEBUG` — bật/tắt debug
- `SECRET_KEY` — khóa bí mật Django
- `DATABASE_URL` hoặc `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `REDIS_URL` — nếu dùng Celery/Channels
- `EMAIL_*` — cấu hình gửi email (nếu cần)

Luôn kiểm tra `.env.example` để biết đầy đủ trường cần thiết.

## Celery

Để chạy worker Celery trong môi trường local:

```powershell
# worker
celery -A onetop_backend.celery worker -l info
# nếu cần scheduler (beat)
celery -A onetop_backend.celery beat -l info
```

Lưu ý: Celery cần broker (Redis / RabbitMQ) — đảm bảo `REDIS_URL` hoặc broker khác đã cấu hình.

## Docker (docker-compose)

Repo có file `docker-compose.yml` và `Dockerfile` để chạy dịch vụ bằng Docker. Ví dụ:

```powershell
docker-compose up --build
```

Kiểm tra file `docker-compose.yml` để biết các service (web, db, redis, celery, ...).

## Kiểm thử

Chạy test Django:

```powershell
python manage.py test
```

Bạn có thể chạy test từng app, ví dụ:

```powershell
python manage.py test apps.chats
```

## Cấu trúc chính của backend

- `manage.py` — entry point Django
- `requirements.txt` — dependencies
- `apps/` — các ứng dụng Django theo module (users, companies, jobs, chats, ...)
- `onetop_backend/` — cấu hình project (settings, asgi, wsgi, celery)
- `Dockerfile`, `docker-compose.yml` — cấu hình container

## Gợi ý phát triển

- Sử dụng `.env` để tách cấu hình môi trường
- Dùng Docker khi cần tái tạo môi trường nhanh
- Kiểm tra `apps/*/tests.py` để đảm bảo các thay đổi không phá vỡ tính năng

## Đóng góp

Mở PR kèm mô tả rõ ràng, cập nhật tests nếu cần. Tuân thủ coding style của dự án.

## Liên hệ

Nếu cần trợ giúp, liên hệ người chịu trách nhiệm dự án hoặc mở issue trên repository.
