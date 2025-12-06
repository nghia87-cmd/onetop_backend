# apps/jobs/tasks.py

import logging
from celery import shared_task, chain
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from datetime import timedelta
# [NÂNG CẤP] Import các class xử lý email chuyên nghiệp
from django.core.mail import get_connection, EmailMultiAlternatives
from apps.users.models import User
from .models import Job
# [OPTIMIZATION] Import Elasticsearch để tìm kiếm nhanh
from elasticsearch_dsl import Q as ES_Q
from .documents import JobDocument

logger = logging.getLogger(__name__)

# Batch size từ settings (có thể config theo tài nguyên server)
BATCH_SIZE = getattr(settings, 'JOB_ALERT_BATCH_SIZE', 500)

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_daily_job_alerts(self):
    """
    Task điều phối: Xác định danh sách ID ứng viên và tạo chuỗi task xử lý lô.
    
    Retry configuration:
    - max_retries: 3 lần
    - default_retry_delay: 300 giây (5 phút)
    - Retry khi gặp lỗi Redis, Elasticsearch, hoặc Database timeout
    """
    try:
        logger.info("Starting daily job alert dispatch task...")
        
        # Chỉ lấy ID để tiết kiệm bộ nhớ
        candidate_ids = list(User.objects.filter(
            user_type=User.UserType.CANDIDATE,
            is_active=True
            # is_verified=True # Bỏ comment nếu có trường này
        ).values_list('id', flat=True))
        
        total_candidates = len(candidate_ids)
        
        if total_candidates == 0:
            logger.info("No candidates found to send alerts.")
            return "No candidates processed."

        # Chia nhỏ task (Batching)
        task_chain = []
        for i in range(0, total_candidates, BATCH_SIZE):
            batch_ids = candidate_ids[i:i + BATCH_SIZE]
            task_chain.append(bulk_create_daily_job_alerts.s(batch_ids))

        # Chạy chuỗi task bất đồng bộ
        if task_chain:
            chain(task_chain).apply_async()
            return f"Dispatched {len(task_chain)} batches for {total_candidates} candidates."
        
        return "No candidates processed."
    
    except Exception as exc:
        # Retry với backoff khi gặp lỗi (Redis timeout, ES unreachable, etc.)
        logger.error(f"Job alert dispatch failed: {exc}")
        raise self.retry(exc=exc, countdown=self.default_retry_delay)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def bulk_create_daily_job_alerts(self, candidate_ids):
    """
    Task xử lý lô: Tối ưu với Elasticsearch thay vì Python loop
    
    Retry configuration:
    - max_retries: 2 lần (ít hơn parent task vì đã batch)
    - default_retry_delay: 60 giây
    """
    try:
        logger.info(f"Processing batch of {len(candidate_ids)} candidates.")
        
        # 1. Lấy danh sách Job mới trong 24h qua
        one_day_ago = timezone.now() - timedelta(days=1)
        
        candidates_batch = User.objects.filter(id__in=candidate_ids).only(
            'id', 'email', 'full_name', 'desired_job_title', 'desired_location'
        )
        
        # Danh sách chứa các đối tượng Email sẽ gửi
        messages = []

        # 2. Sử dụng Elasticsearch để tìm kiếm thay vì Python loop
        for candidate in candidates_batch.iterator():
            # Lấy tiêu chí của ứng viên
            target_title = getattr(candidate, 'desired_job_title', None) or ""
            target_location = getattr(candidate, 'desired_location', None) or ""

            if not target_title and not target_location:
                continue 

            # Tạo query Elasticsearch
            search = JobDocument.search()
            
            # Filter theo thời gian và status
            search = search.filter('range', created_at={'gte': one_day_ago})
            search = search.filter('term', status='PUBLISHED')
            
            # Build query điều kiện OR cho title và location
            queries = []
            if target_title:
                # Match fuzzy cho title (cho phép sai chính tả nhẹ)
                queries.append(ES_Q('match', title={'query': target_title, 'fuzziness': 'AUTO'}))
            
            if target_location:
                # Match fuzzy cho location
                queries.append(ES_Q('match', location={'query': target_location, 'fuzziness': 'AUTO'}))
            
            # Kết hợp queries với OR
            if queries:
                search = search.query('bool', should=queries, minimum_should_match=1)
            
            # Giới hạn 5 job/mail, sắp xếp theo created_at mới nhất
            search = search.sort('-created_at')[:5]
            
            # Execute query và lấy kết quả
            try:
                response = search.execute()
                
                if not response.hits:
                    continue
                
                # Convert Elasticsearch hits thành Job objects
                job_ids = [hit.meta.id for hit in response.hits]
                matched_jobs = Job.objects.filter(id__in=job_ids).select_related('company').only(
                    'id', 'title', 'location', 'salary_min', 'salary_max', 'company__name', 'slug'
                )
                
                if not matched_jobs:
                    continue
                    
            except Exception as e:
                logger.error(f"Elasticsearch query failed for candidate {candidate.id}: {str(e)}")
                continue
            
            # 3. Tạo đối tượng Email
            context = {
                'user': candidate,
                'jobs': matched_jobs,
                'SITE_URL': getattr(settings, 'FRONTEND_URL', 'http://localhost:3000') 
            }
            
            subject = "🔥 Việc làm mới phù hợp với bạn hôm nay!"
            html_content = render_to_string('emails/daily_job_alert.html', context)
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[candidate.email]
            )
            email.attach_alternative(html_content, "text/html")
            messages.append(email)

        # 4. Gửi email hàng loạt qua 1 kết nối duy nhất
        if messages:
            try:
                connection = get_connection()
                connection.open()
                sent_count = connection.send_messages(messages)
                connection.close()
                logger.info(f"Successfully sent {sent_count} job alert emails.")
                return f"Processed batch. Sent {sent_count} emails."
                
            except Exception as e:
                logger.error(f"Failed to send bulk emails: {str(e)}")
                # Retry nếu lỗi network hoặc SMTP timeout
                raise self.retry(exc=e, countdown=self.default_retry_delay)
        
        return "Processed batch. No emails sent."
    
    except Exception as exc:
        # Retry nếu lỗi Elasticsearch hoặc Database
        logger.error(f"Batch processing failed: {exc}")
        raise self.retry(exc=exc, countdown=self.default_retry_delay)