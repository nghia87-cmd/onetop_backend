# apps/jobs/tasks.py
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db.models import Q
from apps.resumes.models import Resume
from .models import Job

User = get_user_model()

@shared_task
def send_daily_job_alerts():
    """
    Task chạy mỗi sáng để gửi email gợi ý việc làm mới cho ứng viên.
    """
    # 1. Lấy các Job mới được đăng trong 24h qua
    yesterday = timezone.now() - timedelta(days=1)
    new_jobs = Job.objects.filter(created_at__gte=yesterday, status='PUBLISHED').select_related('company')

    if not new_jobs.exists():
        return "Không có việc làm mới nào trong hôm nay."

    # 2. Lấy danh sách Ứng viên
    candidates = User.objects.filter(user_type='CANDIDATE')
    email_count = 0

    for candidate in candidates:
        # Lấy CV chính để biết kỹ năng
        resume = Resume.objects.filter(user=candidate, is_primary=True).first()
        if not resume:
            continue # Bỏ qua nếu chưa có CV

        user_skills = list(resume.skills.values_list('name', flat=True)) # VD: ['Python', 'Django']
        
        # 3. Tìm việc phù hợp trong đám job mới (Logic giống Recommendation)
        matched_jobs = []
        for job in new_jobs:
            # Kiểm tra tiêu đề
            if resume.title and resume.title.lower() in job.title.lower():
                matched_jobs.append(job)
                continue
            
            # Kiểm tra kỹ năng (Nếu job requirements chứa bất kỳ skill nào của user)
            for skill in user_skills:
                if skill.lower() in job.requirements.lower():
                    matched_jobs.append(job)
                    break
        
        # 4. Gửi email nếu có job phù hợp
        if matched_jobs:
            subject = f"🔥 {len(matched_jobs)} việc làm mới phù hợp với bạn hôm nay!"
            
            message = f"Xin chào {candidate.full_name},\n\n"
            message += "Dưới đây là các công việc mới nhất dành cho bạn:\n\n"
            
            for job in matched_jobs[:5]: # Chỉ lấy tối đa 5 job
                message += f"📌 {job.title}\n"
                message += f"   Công ty: {job.company.name}\n"
                message += f"   Lương: {job.salary_min or 'TT'} - {job.salary_max or 'TT'}\n"
                message += f"   Địa điểm: {job.location}\n\n"
            
            message += "Hãy truy cập OneTop ngay để ứng tuyển!\n"
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [candidate.email],
                    fail_silently=False,
                )
                email_count += 1
            except Exception as e:
                print(f"Lỗi gửi mail cho {candidate.email}: {e}")

    return f"Đã gửi email báo việc cho {email_count} ứng viên."