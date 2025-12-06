# apps/jobs/tasks.py

import logging
from celery import shared_task, chain
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Q
from apps.users.models import User
from .models import Job
from datetime import timedelta
from django.core.mail import send_mass_mail # Cần import thêm

logger = logging.getLogger(__name__)

# Kích thước lô (batch size)
BATCH_SIZE = 500 # Kích thước lý tưởng, có thể điều chỉnh

# ====================================================================
# [ĐIỂM YẾU 2] TASK ĐIỀU PHỐI (DISPATCHER)
# ====================================================================
@shared_task
def send_daily_job_alerts():
    """
    Task điều phối: Xác định danh sách ID ứng viên và tạo chuỗi task xử lý lô.
    """
    logger.info("Starting daily job alert dispatch task...")
    
    # Chỉ lấy ID của các ứng viên để tiết kiệm bộ nhớ
    # Dùng values_list(..., flat=True) để lấy danh sách ID tối giản
    candidate_ids = list(User.objects.filter(
        user_type=User.UserType.CANDIDATE,
        is_active=True,
        is_verified=True # Chỉ gửi cho user đã verified
    ).values_list('id', flat=True))
    
    total_candidates = len(candidate_ids)
    
    if total_candidates == 0:
        logger.info("No candidates found to send alerts.")
        return "No candidates processed."

    # Chia danh sách ID thành các lô nhỏ (Batching)
    task_chain = []
    for i in range(0, total_candidates, BATCH_SIZE):
        batch_ids = candidate_ids[i:i + BATCH_SIZE]
        # Thêm task xử lý lô vào chuỗi
        task_chain.append(bulk_create_daily_job_alerts.s(batch_ids))

    # Chạy chuỗi task (chain) bất đồng bộ
    if task_chain:
        chain(task_chain).apply_async()
        logger.info(f"Dispatched {len(task_chain)} batches for a total of {total_candidates} candidates.")
        return f"Dispatched {len(task_chain)} batches for a total of {total_candidates} candidates."
    
    return "No candidates processed."


# ====================================================================
# [ĐIỂM YẾU 2] TASK XỬ LÝ LÔ (BATCH PROCESSOR)
# ====================================================================
@shared_task
def bulk_create_daily_job_alerts(candidate_ids):
    """
    Task xử lý lô: Xử lý thông báo việc làm cho một lô ứng viên.
    """
    logger.info(f"Processing job alerts for a batch of {len(candidate_ids)} candidates.")
    
    candidates_batch = User.objects.filter(id__in=candidate_ids)
    one_day_ago = timezone.now() - timedelta(days=1)
    
    emails_to_send = []

    # SỬ DỤNG .iterator() để giảm bộ nhớ khi xử lý từng ứng viên
    for candidate in candidates_batch.iterator(): 
        # Logic tìm việc làm
        job_query = Q()
        if candidate.desired_job_title:
            job_query |= Q(title__icontains=candidate.desired_job_title)
        if candidate.desired_location:
            job_query |= Q(location__icontains=candidate.desired_location)

        relevant_jobs = Job.objects.filter(
            job_query,
            created_at__gte=one_day_ago,
            is_active=True
        ).select_related('company_profile').order_by('-created_at')[:5]

        if relevant_jobs:
            context = {
                'user': candidate,
                'jobs': relevant_jobs,
                'SITE_URL': getattr(settings, 'FRONTEND_URL', 'http://localhost:3000') 
            }
            html_message = render_to_string('emails/daily_job_alert.html', context)
            
            emails_to_send.append(
                (
                    "Job Alert: New Opportunities Await!",
                    candidate.email,
                    html_message
                )
            )

    # Dùng send_mass_mail để gửi email hàng loạt
    if emails_to_send:
        # Tách việc gửi ra một task khác để quản lý lỗi dễ hơn (tùy chọn)
        send_mass_emails_task.delay(emails_to_send)
        logger.info(f"Dispatched {len(emails_to_send)} job alert emails for batch.")

    return f"Processed batch of {len(candidate_ids)} candidates. Dispatched {len(emails_to_send)} emails."


@shared_task(rate_limit="10/s") # Giới hạn 10 email/giây để tránh bị server email block
def send_mass_emails_task(email_data_list):
    """
    Task gửi email hàng loạt thực tế
    email_data_list: List of (subject, recipient, html_content)
    """
    messages = []
    for subject, recipient, html_content in email_data_list:
        messages.append((
            subject,
            "Please view this email in an HTML-compatible client.", # Body text
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            html_message
        ))
    
    # send_mass_mail cần một tuple
    send_mass_mail(tuple(messages), fail_silently=False)
    
    logger.info(f"Successfully sent {len(messages)} mass emails.")
    return f"Successfully sent {len(messages)} mass emails."