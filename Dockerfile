# Sử dụng Python 3.12 (Phiên bản mới nhất, ổn định)
FROM python:3.12-slim-bookworm

# Thiết lập biến môi trường
# Ngăn Python tạo file .pyc và in log ngay lập tức
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Thư mục làm việc trong container
WORKDIR /app

# Cài đặt các gói hệ thống cần thiết (cho Postgres, biên dịch...)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy file thư viện và cài đặt
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code vào container
COPY . .

# Mở port 8000
EXPOSE 8000

# Lệnh chạy mặc định (Dùng Daphne cho WebSocket)
# Lưu ý: Tên project của bạn là onetop_backend
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "onetop_backend.asgi:application"]