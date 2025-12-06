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

logger = logging.getLogger(__name__)

BATCH_SIZE = 500

@shared_task
def send_daily_job_alerts():
    """
    Task điều phối: Xác định danh sách ID ứng viên và tạo chuỗi task xử lý lô.
    """
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

@shared_task
def bulk_create_daily_job_alerts(candidate_ids):
    """
    Task xử lý lô: Tối ưu N+1 Query và Sử dụng Single SMTP Connection
    """
    logger.info(f"Processing batch of {len(candidate_ids)} candidates.")
    
    # 1. Lấy danh sách Job mới trong 24h qua MỘT LẦN DUY NHẤT
    one_day_ago = timezone.now() - timedelta(days=1)
    
    # Chỉ lấy các trường cần thiết -> Giảm tải RAM
    new_jobs = list(Job.objects.filter(
        created_at__gte=one_day_ago,
        status='PUBLISHED'
    ).select_related('company').only(
        'id', 'title', 'location', 'salary_min', 'salary_max', 'company__name'
    ))

    if not new_jobs:
        return "No new jobs found today. Skip sending."

    candidates_batch = User.objects.filter(id__in=candidate_ids)
    
    # Danh sách chứa các đối tượng Email sẽ gửi
    messages = []

    # 2. Xử lý logic so khớp trong bộ nhớ (Python Memory)
    for candidate in candidates_batch.iterator():
        matched_jobs = []
        
        # Lấy tiêu chí của ứng viên an toàn (tránh lỗi AttributeError nếu field null)
        target_title = candidate.desired_job_title.lower() if getattr(candidate, 'desired_job_title', None) else ""
        target_location = candidate.desired_location.lower() if getattr(candidate, 'desired_location', None) else ""

        if not target_title and not target_location:
            continue 

        # So khớp
        for job in new_jobs:
            title_match = target_title in job.title.lower() if target_title else False
            location_match = target_location in job.location.lower() if target_location else False
            
            if title_match or location_match:
                matched_jobs.append(job)
                if len(matched_jobs) >= 5: # Giới hạn 5 job/mail
                    break
        
        # 3. Tạo đối tượng Email (Chưa gửi ngay)
        if matched_jobs:
            context = {
                'user': candidate,
                'jobs': matched_jobs,
                'SITE_URL': getattr(settings, 'FRONTEND_URL', 'http://localhost:3000') 
            }
            
            subject = "🔥 Việc làm mới phù hợp với bạn hôm nay!"
            html_content = render_to_string('emails/daily_job_alert.html', context)
            text_content = strip_tags(html_content) # Tạo bản text thuần cho client không hỗ trợ HTML
            
            # Tạo đối tượng EmailMultiAlternatives
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content, # Nội dung plain text
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[candidate.email]
            )
            # Đính kèm nội dung HTML
            email.attach_alternative(html_content, "text/html")
            
            messages.append(email)

    # 4. Gửi email hàng loạt (Bulk Send) qua 1 kết nối duy nhất
    if messages:
        try:
            # Mở kết nối SMTP thủ công
            connection = get_connection()
            connection.open()
            
            # Gửi toàn bộ danh sách messages
            # send_messages sẽ trả về số lượng email gửi thành công
            sent_count = connection.send_messages(messages)
            
            connection.close()
            logger.info(f"Successfully sent {sent_count} job alert emails.")
            return f"Processed batch. Sent {sent_count} emails."
            
        except Exception as e:
            logger.error(f"Failed to send bulk emails: {str(e)}")
            return f"Failed to send bulk emails: {str(e)}"
    
    return "Processed batch. No emails sent."