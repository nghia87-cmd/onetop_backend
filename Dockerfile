# ==========================================
# GIAI ĐOẠN 1: Builder (Dùng để cài đặt thư viện)
# ==========================================
# [FIX] Đổi 'as' thành 'AS' để khớp với 'FROM'
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 1. Cài đặt các gói hệ thống CẦN THIẾT ĐỂ BUILD (Compiler)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    pkg-config \
    python3-dev \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Tạo virtual environment để cô lập dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 3. Cài đặt Python Dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==========================================
# GIAI ĐOẠN 2: Runner (Image cuối cùng để chạy)
# ==========================================
FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

# 4. Cài đặt các gói hệ thống CẦN THIẾT ĐỂ CHẠY (Runtime libraries)
RUN apt-get update && apt-get install -y \
    libpq5 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# 5. Tạo user non-root để tăng bảo mật
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser

# 6. Copy thư viện đã cài từ giai đoạn Builder sang
COPY --from=builder /opt/venv /opt/venv

# 7. Copy code dự án
COPY . .

# 8. Phân quyền sở hữu file cho user mới
RUN chown -R appuser:appgroup /app

# 9. Chuyển sang user non-root
USER appuser

# Mở port
EXPOSE 8000

# Chạy server với Daphne
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "onetop_backend.asgi:application"]