# Sử dụng Python 3.12
FROM python:3.12-slim-bookworm

# Thiết lập biến môi trường
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Thư mục làm việc
WORKDIR /app

# --- SỬA ĐOẠN NÀY ---
# Cài đặt các gói hệ thống cần thiết
# Thêm: libcairo2-dev, pkg-config, libpango-1.0-0... (Cho PyCairo & xhtml2pdf)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    libcairo2-dev \
    pkg-config \
    python3-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*
# --------------------

# Copy file thư viện và cài đặt
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code
COPY . .

# Mở port
EXPOSE 8000

# Chạy server
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "onetop_backend.asgi:application"]