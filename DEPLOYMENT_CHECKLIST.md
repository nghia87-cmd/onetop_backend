# Production Deployment Checklist

## 🚀 Pre-Deployment Configuration

### 1. Environment Variables (.env)
Copy `.env.example` to `.env` and configure all required variables:

```bash
cp .env.example .env
```

**Critical Variables (MUST SET):**
```bash
# Security
DEBUG=False
SECRET_KEY=<generate-with-python-get_random_secret_key>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# CRITICAL: CSRF Protection for cross-origin requests
# MUST include HTTPS protocol and all frontend domains
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com,https://admin.yourdomain.com

# Database
DATABASE_URL=postgres://user:password@db-host:5432/onetop_db

# Redis
REDIS_URL=redis://redis-host:6379/0

# Frontend
FRONTEND_URL=https://yourdomain.com

# Email (Production SMTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=OneTop <noreply@yourdomain.com>

# Sentry (Error Tracking)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1

# Elasticsearch (Async Indexing)
ELASTICSEARCH_DSL_SIGNAL_PROCESSOR=django_elasticsearch_dsl.signals.CelerySignalProcessor
```

**Performance Tuning Variables:**
```bash
# Rate Limits (tune based on traffic)
PDF_GENERATION_RATE=10/hour  # Increase for high traffic
APPLICATION_SUBMISSION_RATE=50/day
MESSAGE_SEND_RATE=200/hour

# Batch Processing
JOB_ALERT_BATCH_SIZE=1000  # Increase for more users

# Concurrency Control
USE_OPTIMISTIC_LOCKING=True  # Enable for > 10k concurrent users
OPTIMISTIC_LOCK_MAX_RETRIES=5
```

---

## 🐳 Docker Deployment

### docker-compose.yml
```yaml
version: '3.8'

services:
  # PostgreSQL Database
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: onetop_db
      POSTGRES_USER: onetop_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U onetop_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis (Cache + Celery + Channels)
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # Elasticsearch
  elasticsearch:
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"  # 1GB heap
      - xpack.security.enabled=false
    volumes:
      - es_data:/usr/share/elasticsearch/data
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5

  # Django Backend
  backend:
    build: .
    command: gunicorn onetop_backend.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
      - ELASTICSEARCH_DSL_SIGNAL_PROCESSOR=django_elasticsearch_dsl.signals.CelerySignalProcessor
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      elasticsearch:
        condition: service_healthy
    volumes:
      - media_files:/app/media
      - static_files:/app/staticfiles

  # Celery Worker (Default Queue - lightweight tasks)
  celery_worker:
    build: .
    command: celery -A onetop_backend worker -Q celery --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
      - db
    deploy:
      resources:
        limits:
          memory: 1G

  # Celery Heavy Worker (PDF generation - RAM intensive)
  celery_heavy_worker:
    build: .
    command: celery -A onetop_backend worker -Q heavy_tasks --loglevel=info --concurrency=2
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
      - db
    deploy:
      resources:
        limits:
          memory: 2G  # Higher memory for WeasyPrint PDF generation

  # Celery Beat (Scheduler)
  celery_beat:
    build: .
    command: celery -A onetop_backend beat --loglevel=info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
      - db

  # Daphne (WebSocket Server)
  daphne:
    build: .
    command: daphne -b 0.0.0.0 -p 8001 onetop_backend.asgi:application
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
      - db

  # Nginx (Reverse Proxy)
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - media_files:/app/media
      - static_files:/app/staticfiles
      - ./ssl:/etc/nginx/ssl  # SSL certificates
    depends_on:
      - backend
      - daphne

volumes:
  postgres_data:
  redis_data:
  es_data:
  media_files:
  static_files:
```

---

## 🔧 Database Migrations

```bash
# Run all migrations
docker-compose exec backend python manage.py migrate

# Create Elasticsearch index
docker-compose exec backend python manage.py search_index --rebuild -f

# Create superuser
docker-compose exec backend python manage.py createsuperuser
```

---

## 📊 Monitoring Setup

### 1. Sentry Configuration
```python
# Already configured in settings/prod.py
# Just set SENTRY_DSN in .env
```

### 2. Grafana Dashboard
```bash
# Install Prometheus + Grafana
docker-compose -f docker-compose.monitoring.yml up -d
```

**Key Metrics to Monitor:**
- API Response Time (p50, p95, p99)
- Database Query Count
- Redis Cache Hit Rate
- Celery Task Queue Length
- Elasticsearch Indexing Lag
- Payment Transaction Success Rate

### 3. Log Aggregation (ELK Stack)
```yaml
# docker-compose.monitoring.yml
services:
  logstash:
    image: logstash:8.11.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    depends_on:
      - elasticsearch

  kibana:
    image: kibana:8.11.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
```

---

## 🧪 Load Testing

### Using Locust
```python
# locustfile.py
from locust import HttpUser, task, between

class OneTopUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Login
        response = self.client.post("/api/auth/login/", json={
            "email": "test@example.com",
            "password": "test123"
        })
        self.token = response.json()["access"]
    
    @task(10)
    def view_jobs(self):
        self.client.get("/api/jobs/", headers={
            "Authorization": f"Bearer {self.token}"
        })
    
    @task(5)
    def search_jobs(self):
        self.client.get("/api/jobs/?search=backend developer", headers={
            "Authorization": f"Bearer {self.token}"
        })
    
    @task(3)
    def apply_job(self):
        self.client.post("/api/applications/", json={
            "job": 1,
            "cover_letter": "I am interested..."
        }, headers={
            "Authorization": f"Bearer {self.token}"
        })
    
    @task(1)
    def create_payment(self):
        self.client.post("/api/payments/create_payment/", json={
            "package_id": 1
        }, headers={
            "Authorization": f"Bearer {self.token}",
            "Idempotency-Key": f"test-{self.environment.runner.user_count}"
        })

# Run test
# locust -f locustfile.py --host=http://localhost:8000 --users=1000 --spawn-rate=10
```

**Performance Benchmarks:**
- Target: 1000 concurrent users
- API Response Time: < 200ms (p95)
- Database CPU: < 70%
- Redis Hit Rate: > 90%
- Celery Queue Lag: < 10 seconds

---

## 🔐 Security Checklist

- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY` (min 50 chars)
- [ ] HTTPS enabled (SSL certificates)
- [ ] `ALLOWED_HOSTS` configured
- [ ] Database user has minimal privileges
- [ ] Redis protected with password
- [ ] CORS origins whitelist only
- [ ] File upload validators active
- [ ] Rate limiting enabled
- [ ] Sentry error tracking active

---

## 📈 Scaling Recommendations

### Horizontal Scaling
```bash
# Scale Celery workers
docker-compose up -d --scale celery_worker=5

# Scale backend servers (behind load balancer)
docker-compose up -d --scale backend=3
```

### Database Optimization
```sql
-- Add indexes for frequently queried fields
CREATE INDEX idx_jobs_status_created ON jobs_job(status, created_at DESC) WHERE is_deleted = false;
CREATE INDEX idx_applications_candidate_status ON applications_application(candidate_id, status);
CREATE INDEX idx_transactions_user_status ON payments_transaction(user_id, status, created_at DESC);

-- Partition large tables
CREATE TABLE chats_message_2025_12 PARTITION OF chats_message
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');
```

### Redis Configuration
```conf
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1  # Snapshot every 15min if 1 key changed
save 300 10
save 60 10000
```

---

## 🎯 Post-Deployment Verification

### Health Checks
```bash
# Backend
curl https://yourdomain.com/api/health/

# Elasticsearch
curl http://elasticsearch:9200/_cluster/health

# Redis
redis-cli ping

# Celery
celery -A onetop_backend inspect active
```

### Smoke Tests
```bash
# Test critical flows
1. User registration (CANDIDATE + RECRUITER)
2. Job posting (with credits)
3. Application submission
4. Payment transaction (VNPay)
5. WebSocket chat
6. Email notifications
7. PDF generation
```

---

## 📞 Support & Monitoring

### Alert Rules (Sentry/PagerDuty)
- API error rate > 5%
- Database query time > 1s
- Celery queue length > 1000
- Payment failure rate > 10%
- Redis cache hit rate < 80%
- Disk usage > 85%

### On-Call Runbook
```bash
# High CPU on database
→ Check slow queries: SELECT * FROM pg_stat_activity;
→ Kill long-running queries: SELECT pg_terminate_backend(pid);

# Celery queue backup
→ Check worker status: celery -A onetop_backend inspect active
→ Scale workers: docker-compose up -d --scale celery_worker=10

# Elasticsearch out of sync
→ Rebuild index: python manage.py search_index --rebuild -f

# Redis memory full
→ Clear cache: redis-cli FLUSHDB
→ Increase maxmemory limit
```

---

## ✅ Final Production Checklist

- [ ] All environment variables set in `.env`
- [ ] Database migrations applied
- [ ] Elasticsearch index created
- [ ] Superuser account created
- [ ] Static files collected
- [ ] Media files directory permissions set
- [ ] SSL certificates installed
- [ ] Nginx configured and tested
- [ ] Load balancer configured
- [ ] Monitoring dashboards active
- [ ] Backup strategy implemented
- [ ] Incident response plan documented
- [ ] Team trained on deployment process

---

**Ready for Production Deployment!** 🚀

For questions or issues, check:
- Documentation: `FINAL_PRODUCTION_READY.md`
- Architecture: `PHASE3_ENTERPRISE_ENHANCEMENTS.md`
- Bug Fixes: `CRITICAL_BUGS_ROUND2.md`
- Optimizations: `OPTIMIZATION_FIXES.md`
- Deep Audit: `DEEP_CODE_AUDIT.md`
